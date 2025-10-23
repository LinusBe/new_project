
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DataFile
# Wichtig: HttpResponse hinzugefügt
from django.http import FileResponse, Http404, HttpResponseForbidden, HttpResponse
from django.contrib import messages
import pandas as pd
import io
import logging
import chardet
import numpy as np

# NEU: Import pyarrow
try:
    import pyarrow as pa
    import pyarrow.ipc as ipc
    import pyarrow.parquet as
 pq
except ImportError:
    pa = None
    ipc = None
    pq = None
    logging.warning("pyarrow not installed.
 Analysis functionality requires 'pip install pyarrow'.")
from django.conf import settings
from .cache import (
    get_cache_path_for, read_cached_table, ensure_parquet_cache_for_single_table,
    ensure_parquet_cache_for_excel, SHEET_DEFAULT
)
logger = logging.getLogger(__name__)

# --- Hilfsfunktionen (Robustes Laden und Typ-Optimierung) ---

def optimize_dataframe_types(df):
    """
    Versucht, die Datentypen der Spalten intelligent zu konvertieren (Text zu Zahlen/Datum).
 Setzt voraus, dass die Daten initial robust als Text geladen wurden.
 """
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]):
            original_series = df[col]

            # 1. Versuch Numerisch (Robust gegenüber Formatierungen)
            try:
                # Bereinige Whitespace
                temp_series = original_series.str.strip()


                # Versuch Standard-Konvertierung
                converted_series = pd.to_numeric(temp_series, errors='coerce')

                # Prüfen, ob die Konvertierung sinnvoll war (mindestens eine Zahl erkannt, außer Spalte war leer)

                 if not (converted_series.isnull().all() and not original_series.isnull().all()):
                    df[col] = converted_series
                    continue

                # Wenn Standard fehlschlug: Aggressiveres Cleaning (z.B. Währungssymbole, Tausendertrenner schwer robust zu erkennen)

    # Entferne gängige Währungssymbole und Whitespace
                temp_series = temp_series.replace({r'[€$£\s]': ''}, regex=True)
                converted_series = pd.to_numeric(temp_series, errors='coerce')
                if not (converted_series.isnull().all() and not original_series.isnull().all()):
                   df[col] = converted_series

               continue

            except Exception as e:
                logger.debug(f"Numerische Konvertierung für Spalte {col} fehlgeschlagen: {e}")


            # 2. Versuch Datum
            try:
                #
  infer_datetime_format=True beschleunigt erheblich
                # dayfirst=True hilft bei deutschen Formaten (z.B.
 31.12.2025)
                converted_series = pd.to_datetime(df[col], errors='coerce', infer_datetime_format=True, dayfirst=True)
                if not (converted_series.isnull().all() and not original_series.isnull().all()):
                    df[col] = converted_series
                    continue
            except Exception as e:

                 logger.debug(f"Datums-Konvertierung für Spalte {col} fehlgeschlagen: {e}")
    return df

def read_csv_robust(file_content_bytes):
    """Liest CSVs mit automatischem Encoding und Separator Sniffing."""
    detection = chardet.detect(file_content_bytes[:307200]) # Analysebereich vergrößert (300KB)
    encoding = detection.get('encoding')
    if not encoding: encoding = 'utf-8'

    separators = [',', ';', '\t', '|']
    # cp1252 (Windows Western) hinzugefügt für bessere Kompatibilität
    encodings_to_try = list(dict.fromkeys(filter(None, [encoding, 'utf-8', 'latin1', 'cp1252'])))

    best_df = None

      max_cols = 0

    for enc in encodings_to_try:
        try:
            decoded_content = file_content_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
        for separator in separators:
            try:
                # WICHTIG:

                # low_memory=False für große CSVs.
 # dtype=str: Lies alles als Text. Dies ist der robusteste Weg. Die Typisierung erfolgt später.
 df = pd.read_csv(io.StringIO(decoded_content), sep=separator, engine='python', low_memory=False, dtype=str)

                num_cols = len(df.columns)
                if num_cols > max_cols:
                    max_cols = num_cols

     best_df = df
                if num_cols > 1: return df

            except Exception:
                continue

    if best_df is not None: return best_df
    raise ValueError("Konnte das CSV-Format (Encoding/Separator) nicht zuverlässig bestimmen.")

@login_required
def download_file(request, file_id):
    # (Implementierung wie zuvor, robust)
    try:

 f = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        if DataFile.objects.filter(pk=file_id).exists():
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    # Existenzprüfung entfernt, da FileResponse dies handhabt oder Fehler wirft.
 try:
        # Nutze f.file.open('rb') für Kompatibilität mit verschiedenen Storage Backends
        return FileResponse(f.file.open('rb'), as_attachment=True, filename=f.filename())
    except FileNotFoundError:
        raise Http404("Datei nicht im Speicher vorhanden.")
    except Exception as e:
        logger.error(f"Error serving file {file_id}: {e}")
        messages.error(request, "Beim Herunterladen der Datei ist ein Fehler aufgetreten.")
        return redirect('dashboard')

# --- Haupt-Analyse View Struktur ---

@login_required
def analyze_file(request, file_id):

 if pa is None:
        messages.error(request, "Analysefunktion deaktiviert. Die Server-Abhängigkeit PyArrow fehlt.")
        return redirect('dashboard')

    # 1. Sicherheitsprüfung
    try:
        data_file = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        if DataFile.objects.filter(pk=file_id).exists():
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    if not data_file.is_analyzable():

          messages.warning(request, f"Dieser Dateityp kann nicht online analysiert werden.")
         return redirect('dashboard')

    # 2. Angeforderter Modus bestimmen
    output_format = request.GET.get('format', 'html')
    selected_sheet = request.GET.get('sheet', None)
    force_refresh = request.GET.get('refresh') in ('1', 'true', 'yes')  # optional

    if output_format == 'html':
        # Modus HTML: Lade das Template
        return render_analysis_template(request, data_file, selected_sheet)

    elif output_format == 'arrow':

          return stream_arrow_data(request, data_file, selected_sheet, force_refresh=force_refresh)

    else:
        return HttpResponse("Ungültiges Format angefordert", status=400)


def render_analysis_template(request, data_file, selected_sheet):
    """Rendert die HTML-Seite, inklusive der Excel-Sheet-Namen."""
    sheet_names = []
    # Schnelles Lesen der Metadaten für die Sheet-Auswahl
    if data_file.get_file_extension() in ['.xlsx', '.xls', '.xlsm']:
        try:
            # Nutze data_file.file.open('rb') für Robustheit

  with data_file.file.open('rb') as f:
                xls = pd.ExcelFile(f)
                sheet_names = xls.sheet_names or []
        except FileNotFoundError:
             raise Http404("Datei nicht im Speicher vorhanden.")
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Excel-Sheets für Datei {data_file.id}: {e}")

             messages.error(request, "Konnte Excel-Arbeitsblätter nicht lesen (verschlüsselt oder korrupt?).")

    # Sicherstellen, dass das ausgewählte Sheet gültig ist
    if selected_sheet not in sheet_names and sheet_names:
        selected_sheet = sheet_names[0]
    elif not sheet_names:
        selected_sheet = None

    return render(request, 'datafiles/analyze.html', {
        'data_file': data_file,
        'sheet_names': sheet_names,
        'selected_sheet': selected_sheet,

       })

def stream_arrow_data(request, data_file, selected_sheet, force_refresh: bool = False):
    """
    Fast Path: Parquet-Sidecar lesen → Arrow IPC streamen.
 Fallback bei Cache-Miss: Rohdatei einlesen, Parquet schreiben, streamen.
    """

    extension = data_file.get_file_extension()
    logger.info(f"[ANALYZE] Start analyze for file_id={data_file.id}, ext={extension}")

    try:
        extension = data_file.get_file_extension()
        table = None

        # 1) Wenn Parquet als Original: direkt lesen (kein Sidecar nötig)
        if extension == '.parquet' and pq is not None:
            with data_file.file.open('rb') as f:

                 # pyarrow.parquet kann auch file-like; bei Storage Backends ggf. Bytes lesen
                file_bytes = f.read()
            table = pq.read_table(io.BytesIO(file_bytes), memory_map=False)

        # 2) Andernfalls: Sidecar-Cache verwenden, falls vorhanden und nicht refresh
        if table is None and not force_refresh:
            table =
  read_cached_table(data_file, selected_sheet)

        # 3) Cache-Miss → Rohdatei einmalig lesen, optimieren, Parquet schreiben
        if table is None:
            df = load_and_process_file(data_file, selected_sheet)

            # Leere Datei/Schnitt?
 if df is None or df.empty:
                # leeren Arrow-Stream zurückgeben (oder 204)
                empty = pa.Table.from_arrays([], names=[])
                logger.info("[ANALYZE] Returning Arrow stream")
                return _arrow_stream_http(empty)

            # Parquet-Cache aktualisieren

             sheet_key = selected_sheet or (SHEET_DEFAULT if extension in ('.csv', '.pkl') else selected_sheet)
            try:
                ensure_parquet_cache_for_single_table(data_file, df, sheet_name=sheet_key)
            except Exception as ex:
                logger.warning(f"Parquet-Cache schreiben fehlgeschlagen (weiter ohne Cache): {ex}")

            # Jetzt Arrow-Table
  aus df erzeugen (einmalig)
            table = pa.Table.from_pandas(df, preserve_index=False)

        # 4) Arrow IPC streamen (RecordBatchStreamWriter, wie Perspective erwartet)
        logger.info("[ANALYZE] Returning Arrow stream")
        return _arrow_stream_http(table)

    except Http404:
        return HttpResponse("Datei nicht gefunden.", status=404)
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten/Konvertieren der Datei {data_file.id} zu Arrow: {e}", exc_info=True)

         # Sende einen HTTP-Fehlerstatus zurück, den das Frontend abfangen kann
        logger.info("[ANALYZE] Returning Arrow stream")
        return HttpResponse(f"Fehler bei der Datenverarbeitung: {e}", status=500)


def _arrow_stream_http(table: "pa.Table") -> HttpResponse:
    sink = pa.BufferOutputStream()
    with ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    buf = sink.getvalue()
    return HttpResponse(buf.to_pybytes(), content_type='application/vnd.apache.arrow.stream')


def load_and_process_file(data_file, selected_sheet=None):
    """
    Rohdaten einlesen (nur bei Cache-Miss/Refresh) und typoptimieren.
 """
    try:
        # Nutze .open('rb') und .read() für Robustheit über Storage Backends
        with data_file.file.open('rb') as f:
            file_content = f.read()
    except FileNotFoundError:
        raise Http404("Datei nicht im Speicher vorhanden.")

    extension = data_file.get_file_extension()
    df = pd.DataFrame()

    # 1. Laden der Rohdaten
    if extension == '.csv':
        df
 = read_csv_robust(file_content)

    elif extension in ['.xlsx', '.xls', '.xlsm']:
        with io.BytesIO(file_content) as bio:
            try:
                xls = pd.ExcelFile(bio)
            except Exception as e:
                raise ValueError(f"Konnte Excel-Datei nicht lesen: {e}")
            sheet_to_read
 = selected_sheet
            # Fallback Logik
            if sheet_to_read not in xls.sheet_names:
                sheet_to_read = xls.sheet_names[0] if xls.sheet_names else None
            df = xls.parse(sheet_to_read, dtype=str) if sheet_to_read else pd.DataFrame()

    elif extension == '.pkl':
        df = pd.read_pickle(io.BytesIO(file_content))

    elif extension == '.parquet' and pq is
 not None:
        # Falls du doch mal einen Parquet-Upload bekommst, hier als Pandas laden
        table = pq.read_table(io.BytesIO(file_content), memory_map=False)
        return table.to_pandas(types_mapper=None)

    if not df.empty:
        df.replace(['', ' '], np.nan, inplace=True)
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)

        # Spaltennamen säubern und eindeutig machen
        def _safe_colname(idx,
 col):
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

        # Typ-Optimierung (Zahlen/Datum erkennen)
        df = optimize_dataframe_types(df)

        # WICHTIG für Arrow: Sicherstellen der Typ-Konsistenz (None vs NaN).
 for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].replace({None: np.nan})
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                pass
            elif pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].where(pd.notnull(df[col]), None)

                 mask = df[col].notna()
                if mask.any():
                    df.loc[mask, col] = df.loc[mask, col].astype(str)

    return df
