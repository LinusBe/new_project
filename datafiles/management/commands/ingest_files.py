# datafiles/management/commands/ingest_files.py
import os
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np  # HINZUGEFÜGT: Fehlender Import
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import File
from django.db import transaction

# Correct import path assuming models.py is in the same app directory
from datafiles.models import DataFile
# If models.py is in a different app, adjust the import accordingly, e.g.:
# from ..models import DataFile

USER = get_user_model()

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".xlsm", ".pkl"}  # matches your analysis
FILENAME_USER_REGEXES = [
    re.compile(r"^(?P<username>[a-zA-Z0-9_.-]+)[\W_].*$"),  # username_...
    re.compile(r"^(?P<username>[a-zA-Z0-9_.-]+)$"),         # only username
]

def is_file_stable(p: Path, stability_seconds: int) -> bool:
    """Heuristic: File is 'finished' when mtime has been unchanged for X seconds."""
    try:
        mtime = p.stat().st_mtime
    except FileNotFoundError:
        return False
    return (time.time() - mtime) >= stability_seconds

def ensure_dirs():
    for d in [settings.INBOX_DIR, settings.PROCESSED_DIR, settings.ERROR_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

def move_to(target_dir: Path, src: Path, subdir: str | None = None) -> Path:
    target_dir = Path(target_dir)
    if subdir:
        target_dir = target_dir / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / src.name
    if dest.exists():
        base, ext = dest.stem, dest.suffix
        i = 1
        while True:
            candidate = dest.with_name(f"{base}__v{i}{ext}")
            if not candidate.exists():
                dest = candidate
                break
            i += 1
    src.replace(dest)
    return dest


def extract_username(file_path: Path) -> str | None:
    """Extracts the username from the filename: <username>_rest.ext"""
    stem = file_path.stem
    if "_" in stem:
        return stem.split("_", 1)[0]
    # Optional: Fallback via Regex
    for rx in FILENAME_USER_REGEXES:
        m = rx.match(stem)
        if m:
            return m.group("username")
    return None


def decide_user_for(file_path: Path):
    """
    Returns the Django user for the 
 file (or None).
    No side effects, no logging here!
    """
    username = extract_username(file_path)
    if not username:
        return None
    try:
        return USER.objects.get(username__iexact=username)
    except USER.DoesNotExist:
        return None


class Command(BaseCommand):
    help = "Ingests new files from INBOX_DIR and creates DataFile objects."
    # CORRECTION: Method add_arguments indented correctly
    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run once (for scheduler). Without flag: loop at 10s intervals.",
        )
        parser.add_argument("--interval", type=int, default=10, help="Seconds between scans")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would happen (no write operations).",
        )

    def handle(self, *args, **options):
        ensure_dirs()
        interval = options["interval"]
        run_once = options["once"]
        self.dry_run = options["dry_run"]

        while True:
            self.scan_once()
            if run_once:
                break
            time.sleep(interval)

    def scan_once(self):
        inbox = Path(settings.INBOX_DIR)
        stability = int(getattr(settings, "FILE_STABILITY_SECONDS", 3))
        for p in inbox.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in SUPPORTED_EXTS:
                # ignore (or: move_to(ERROR, ...))
                continue
            if not is_file_stable(p, stability):
                continue

            # Extract username
            username = extract_username(p)
            if not username:
                self.stderr.write(f"[ERROR] No username in filename: {p.name}")
                if not self.dry_run:
                    move_to(Path(settings.ERROR_DIR), p, subdir="no_username")
                continue

            # Processed check
            user_processed_dir = Path(settings.PROCESSED_DIR) / username
            processed_path = user_processed_dir / p.name
            if processed_path.exists():
                self.stdout.write(f"[SKIP] Already processed: {processed_path}")
                continue

            # User lookup
            user = decide_user_for(p)
            if not user:
                self.stderr.write(f"[ERROR] No user found for '{username}' (file: {p.name})")
                if not self.dry_run:
                    move_to(Path(settings.ERROR_DIR), p, subdir="no_owner")
                continue

            # Optional: DB duplicate check
            if DataFile.objects.filter(user=user, title=p.stem).exists():
                self.stdout.write(f"[SKIP] Already in DB (user={user.username}, title={p.stem})")
                if not self.dry_run:
                    move_to(Path(settings.PROCESSED_DIR), p, subdir=username)
                continue

            # Save to Django storage
            storage_rel_path = f"user_{user.id}/{p.name}"
            if self.dry_run:
                self.stdout.write(f"[DRY] Save to storage: {storage_rel_path}")
            else:
                try:
                    with p.open("rb") as fh:
                        saved_path = default_storage.save(storage_rel_path, File(fh))
                except Exception as ex:
                    self.stderr.write(f"[ERROR] Storage save failed for {p}: {ex}")
                    move_to(Path(settings.ERROR_DIR), p, subdir="storage_error")
                    continue

                # --- Create DataFile (transactional) ---
                try:
                    with transaction.atomic():
                        obj = DataFile.objects.create(
                            user=user,
                            title=p.stem,
                            file=saved_path
                        )
                except Exception as ex:
                    self.stderr.write(f"[ERROR] DataFile.create failed for {p}: {ex}")
                    # Cleanup: delete saved file
                    try:
                        default_storage.delete(saved_path)
                    except Exception:
                        pass
                    move_to(Path(settings.ERROR_DIR), p, subdir="db_error")
                    continue

                # --- Success: Create Parquet cache (new) ---
                try:
                    # Make sure these imports are correct based on your project structure
                    from datafiles.cache import (
                        ensure_parquet_cache_for_excel, ensure_parquet_cache_for_single_table, SHEET_DEFAULT
                    )
                    from datafiles.views import read_csv_robust, optimize_dataframe_types # Reuse Logic

                    # Read original bytes (from Storage - use saved_path if reading from storage after move)
                    # If reading the original file before moving it to processed:
                    with p.open("rb") as fh:
                        original_bytes = fh.read()
                    # Or if reading from Django storage after saving:
                    # with default_storage.open(saved_path, 'rb') as fh:
                    #     original_bytes = fh.read()


                    ext = p.suffix.lower()
                    if ext in {".xlsx", ".xls", ".xlsm"}:
                        import pandas as pd, io
                        # Determine sheet names and cache all of them
                        xls = pd.ExcelFile(io.BytesIO(original_bytes))
                        sheets = xls.sheet_names or []
                        ensure_parquet_cache_for_excel(obj, original_bytes, sheets)

                    elif ext == ".csv":
                        df = read_csv_robust(original_bytes)
                        df.replace(['', ' '], np.nan, inplace=True)
                        df.dropna(how='all', inplace=True)
                        df.dropna(axis=1, how='all', inplace=True)

                        # Clean column names
                        def _safe_colname(idx, col):
                            s = '' if col is None else str(col).strip()
                            if s.startswith('Unnamed:') or s in ('', 'nan', 'NaN', 'None'):
                                return f'Column_{idx+1}'
                            return s
                        cols, seen = [], set()
                        for i, c in enumerate(df.columns):
                            name = _safe_colname(i, c)
                            if name in seen:
                                k, base = 2, name
                                while name in seen:
                                    name = f"{base}_{k}";
                                    k += 1
                            seen.add(name); cols.append(name)
                        df.columns = cols

                        df = optimize_dataframe_types(df)
                        ensure_parquet_cache_for_single_table(obj, df, sheet_name=SHEET_DEFAULT)

                    elif ext == ".pkl":
                        import pandas as pd, io
                        df = pd.read_pickle(io.BytesIO(original_bytes))
                        ensure_parquet_cache_for_single_table(obj, df, sheet_name=SHEET_DEFAULT)

                    # Parquet uploads (.parquet) do not need a sidecar

                except Exception as ex:
                    # On error: do not hard-fail – the analysis flow builds the cache on first call
                    self.stderr.write(f"[WARN] Parquet cache creation during ingest failed: {ex}")

                # Finally, move the original file to the processed directory if successful
                move_to(Path(settings.PROCESSED_DIR), p, subdir=username) # Added missing move operation