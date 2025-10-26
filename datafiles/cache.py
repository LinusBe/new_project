# datafiles/cache.py
from __future__ import annotations
from pathlib import Path
import io
import re
import logging
import pandas as pd
import numpy as np
from django.conf import settings

try:
    import pyarrow as pa
    import pyarrow.ipc as ipc
    import pyarrow.parquet as pq
except ImportError:
    pa = None
    ipc = None
    pq = None

logger = logging.getLogger(__name__)

SHEET_DEFAULT = "data"  # Für CSV/PKL (ein "Sheet")

def _slugify(name: str) -> str:
    name = name.strip()
    # Windows-safe und URL-safe: nur [a-z0-9_-]
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.IGNORECASE)
    return name[:128] or "sheet"

def get_cache_dir_for(data_file) -> Path:
    """
    MEDIA_ROOT/cache/user_<uid>/<datafile_id>/
    """
    base = Path(getattr(settings, "DATA_CACHE_DIR", Path(settings.MEDIA_ROOT) / "cache"))
    return base / f"user_{data_file.user_id}" / str(data_file.id)

def get_cache_path_for(data_file, sheet_name: str | None) -> Path:
    if not sheet_name:
        sheet_key = SHEET_DEFAULT
    else:
        sheet_key = _slugify(sheet_name)
    return get_cache_dir_for(data_file) / f"{sheet_key}.parquet"


def write_parquet_table(table: "pa.Table", dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    kwargs = dict(
        compression=getattr(settings, "PARQUET_COMPRESSION", "zstd"),
        compression_level=getattr(settings, "PARQUET_COMPRESSION_LEVEL", 7),
        use_dictionary=getattr(settings, "PARQUET_USE_DICTIONARY", True),
    )
    # Zeit-Parameter optional anhängen
    ts_kwargs = dict(
        coerce_timestamps=getattr(settings, "PARQUET_COERCE_TIMESTAMPS", "ms"),
        allow_truncated_timestamps=getattr(settings, "PARQUET_TRUNCATE_TIMESTAMPS", True),
    )
    try:
        pq.write_table(table, dest.as_posix(), **kwargs, **ts_kwargs)
    except TypeError:
        # Fallback ohne deprecated/entfernte Timestamp-Parameter
        pq.write_table(table, dest.as_posix(), **kwargs)


def ary_default(_):  # kleiner Trick, um optionalen Wert einzuhängen, ohne globale Var
    return None

def df_to_arrow(df: pd.DataFrame) -> "pa.Table":
    # Sicherstellen, dass df sauber ist
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace({None: np.nan})
        elif pd.api.types.is_object_dtype(df[col]):
            df[col] = df[col].where(pd.notnull(df[col]), None).astype("object")
    return pa.Table.from_pandas(df, preserve_index=False)

def ensure_parquet_cache_for_excel(data_file, content_bytes: bytes, sheet_names: list[str]):
    """
    Erzeugt je Sheet eine Parquet-Datei, falls nicht vorhanden.
    Lädt Sheets initial als Text (dtype=str), Typoptimierung delegierst du an bestehende Logik im View.
    """
    from .views import optimize_dataframe_types  # wiederverwenden, kein doppelter Code
    import pandas as pd
    import io

    if not pa or not pq:
        raise RuntimeError("pyarrow nicht installiert – Parquet-Cache kann nicht erzeugt werden.")

    with io.BytesIO(content_bytes) as bio:
        xls = pd.ExcelFile(bio)  # Engine auto

        for sheet in (sheet_names or xls.sheet_names):
            cache_path = get_cache_path_for(data_file, sheet)
            if cache_path.exists():
                continue
            try:
                df = xls.parse(sheet, dtype=str)
                df.replace(['', ' '], np.nan, inplace=True)
                df.dropna(how='all', inplace=True)
                df.dropna(axis=1, how='all', inplace=True)

                # Spaltennamen robust machen (wie im View)
                def _safe_colname(idx, col):
                    s = '' if col is None else str(col).strip()
                    if s.startswith('Unnamed:') or s in ('', 'nan', 'NaN', 'None'):
                        return f'Spalte_{idx+1}'
                    return s
                
                cols = []
                for i, c in enumerate(df.columns):
                    name = _safe_colname(i, c)
                    original_name = name
                    suffix = 1
                    while name in cols:
                        suffix += 1
                        name = f"{original_name}_{suffix}"
                    cols.append(name)
                df.columns = cols

                df = optimize_dataframe_types(df)
                table = df_to_arrow(df)
                write_parquet_table(table, cache_path)
                logger.info(f"[CACHE] Excel→Parquet: {cache_path}")
            except Exception as ex:
                logger.warning(f"[CACHE] Sheet '{sheet}' konnte nicht konvertiert werden: {ex}")

def ensure_parquet_cache_for_single_table(data_file, df: pd.DataFrame, sheet_name: str | None = None):
    if not pa or not pq:
        raise RuntimeError("pyarrow nicht installiert – Parquet-Cache kann nicht erzeugt werden.")
    table = df_to_arrow(df)
    cache_path = get_cache_path_for(data_file, sheet_name)
    write_parquet_table(table, cache_path)
    return cache_path

def read_cached_table(data_file, sheet_name: str | None):
    """
    Gibt pa.Table aus der Parquet-Sidecar-Datei zurück, falls vorhanden; sonst None.
    """
    if not pa or not pq:
        return None
    p = get_cache_path_for(data_file, sheet_name)
    if p.exists():
        return pq.read_table(p.as_posix(), memory_map=True)
    return None

def purge_cache_for(data_file):
    """
    Löscht den kompletten Cache-Ordner eines DataFile.
    """
    import shutil
    cache_dir = get_cache_dir_for(data_file)
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)