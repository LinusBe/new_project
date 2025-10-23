# datafiles/management/commands/ingest_files.py
import os
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.base import File
from django.db import transaction

from datafiles.models import DataFile

USER
 = get_user_model()

SUPPORTED_EXTS = {".csv", ".xlsx", ".xls", ".xlsm", ".pkl"}  # passt zu deiner Analyse
FILENAME_USER_REGEXES = [
    re.compile(r"^(?P<username>[a-zA-Z0-9_.-]+)[\W_].*$"),  # username_...
    re.compile(r"^(?P<username>[a-zA-Z0-9_.-]+)$"),         # nur username
]

def is_file_stable(p: Path, stability_seconds: int) -> bool:
    """Heuristik: Datei ist 'fertig', wenn mtime seit X Sekunden unverändert."""
    try:
        mtime = p.stat().st_mtime
    except FileNotFoundError:
        return False
    return (time.time() - mtime) >= stability_seconds

def ensure_dirs():
    for d
 in [settings.INBOX_DIR, settings.PROCESSED_DIR, settings.ERROR_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)

def move_to(target_dir: Path, src: Path, subdir: str |
 None = None) -> Path:
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


def extract_username(file_path: Path) -> str |
 None:
    """Extrahiert den Benutzernamen aus dem Dateinamen: <username>_rest.ext"""
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
    Liefert den Django-User für die
 Datei (oder None).
    Keine Side-Effects, kein Logging hier!
    """
    username = extract_username(file_path)
    if not username:
        return None
    try:
        return USER.objects.get(username__iexact=username)
    except USER.DoesNotExist:
        return None


class Command(BaseCommand):
    help = "Ingestiert neue Dateien aus INBOX_DIR und legt DataFile-Objekte an."
 def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Einmal ausführen (für Scheduler). Ohne Flag: Schleife im 10s-Intervall.",
        )
        parser.add_argument("--interval", type=int, default=10, help="Sekunden zwischen Scans")
        parser.add_argument(
            "--dry-run",

             action="store_true",
            help="Nur anzeigen, was passieren würde (keine Schreiboperationen).",
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
                # ignorieren (oder: move_to(ERROR, ...))
                continue
            if not is_file_stable(p, stability):
                continue


         # Username extrahieren
            username = extract_username(p)
            if not username:
                self.stderr.write(f"[ERROR] Kein Username im Dateinamen: {p.name}")
                if not self.dry_run:
                    move_to(Path(settings.ERROR_DIR), p, subdir="no_username")

                continue

            # processed-Check
            user_processed_dir = Path(settings.PROCESSED_DIR) / username
            processed_path = user_processed_dir / p.name
            if processed_path.exists():
                self.stdout.write(f"[SKIP] Bereits verarbeitet: {processed_path}")

           continue

            # User lookup
            user = decide_user_for(p)
            if not user:
                self.stderr.write(f"[ERROR] Kein User gefunden für '{username}' (Datei: {p.name})")
                if not self.dry_run:

          move_to(Path(settings.ERROR_DIR), p, subdir="no_owner")
                continue

            # Optional: DB-Duplikatcheck
            if DataFile.objects.filter(user=user, title=p.stem).exists():
                self.stdout.write(f"[SKIP] Bereits in DB (user={user.username}, title={p.stem})")
                if not self.dry_run:

                     move_to(Path(settings.PROCESSED_DIR), p, subdir=username)
                continue

            # Speichern in Django-Storage
            storage_rel_path = f"user_{user.id}/{p.name}"
            if self.dry_run:
                self.stdout.write(f"[DRY] Save to storage: {storage_rel_path}")

         else:
                try:
                    with p.open("rb") as fh:
                        saved_path = default_storage.save(storage_rel_path, File(fh))
                except Exception as ex:

              self.stderr.write(f"[ERROR] Storage-Save fehlgeschlagen für {p}: {ex}")
                    move_to(Path(settings.ERROR_DIR), p, subdir="storage_error")
                    continue

                # --- DataFile anlegen (transaktional) ---
                try:

                     with transaction.atomic():
                        obj = DataFile.objects.create(
                            user=user,
                            title=p.stem,

                             file=saved_path
                        )
                except Exception as ex:
                    self.stderr.write(f"[ERROR] DataFile.create fehlgeschlagen für {p}: {ex}")

                 # Aufräumen: gespeicherte Datei löschen
                    try:
                        default_storage.delete(saved_path)
                    except Exception:

          pass
                    move_to(Path(settings.ERROR_DIR), p, subdir="db_error")
                    continue

                # --- Erfolgreich: Parquet-Cache erstellen (neu) ---
                try:

                  from datafiles.cache import (
                        ensure_parquet_cache_for_excel, ensure_parquet_cache_for_single_table, SHEET_DEFAULT
                    )
                    from datafiles.views import read_csv_robust, optimize_dataframe_types  # Reuse Logic


      # Originalbytes lesen (aus Storage)
                    with p.open("rb") as fh:
                        original_bytes = fh.read()

                    ext = p.suffix.lower()
                    if ext in {".xlsx",
  ".xls", ".xlsm"}:
                        import pandas as pd, io
                        # Sheet-Namen ermitteln und alle cachen
                        xls = pd.ExcelFile(io.BytesIO(original_bytes))

                  sheets = xls.sheet_names or []
                        ensure_parquet_cache_for_excel(obj, original_bytes, sheets)

                    elif ext == ".csv":
                        df = read_csv_robust(original_bytes)

                         df.replace(['', ' '], np.nan, inplace=True)
                        df.dropna(how='all', inplace=True)
                        df.dropna(axis=1, how='all', inplace=True)

                        # Spaltennamen säubern

                          def _safe_colname(idx, col):
                            s = '' if col is None else str(col).strip()
                            if s.startswith('Unnamed:') or s in ('', 'nan', 'NaN', 'None'):

                              return f'Spalte_{idx+1}'
                            return s
                        cols, seen = [], set()

          for i, c in enumerate(df.columns):
                            name = _safe_colname(i, c)
                            if name in seen:

         k, base = 2, name
                                while name in seen:
                                    name = f"{base}_{k}";
 k += 1
                            seen.add(name);
 cols.append(name)
                        df.columns = cols

                        df = optimize_dataframe_types(df)
                        ensure_parquet_cache_for_single_table(obj, df, sheet_name=SHEET_DEFAULT)

                    elif ext
  == ".pkl":
                        import pandas as pd, io
                        df = pd.read_pickle(io.BytesIO(original_bytes))
                        ensure_parquet_cache_for_single_table(obj, df, sheet_name=SHEET_DEFAULT)


      # Parquet-Uploads (.parquet) brauchen keinen Sidecar

                except Exception as ex:
                    # Bei Fehlern: nicht hart abbrechen – der Analyse-Flow baut Cache beim ersten Aufruf nach
                    self.stderr.write(f"[WARN] Parquet-Cache beim Ingest fehlgeschlagen: {ex}")
