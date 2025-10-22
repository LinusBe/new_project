
Das ist ein sehr wichtiges Feedback. Sie haben das Problem genau richtig erkannt: Die Datentypen werden beim Einlesen nicht korrekt als Zahlen identifiziert.
Ursache des Problems
Wenn Pandas eine Excel- oder CSV-Datei einliest und eine Spalte auch nur einen einzigen Wert enthält, der nicht eindeutig als Zahl erkennbar ist (z.B. eine leere Zelle, Formatierungen oder ein Textkommentar), wird die gesamte Spalte konservativ als Typ object (Text) klassifiziert.
Beim Senden der Daten an das Frontend erhält PivotTable.js dann Text (z.B. "123") anstelle von Zahlen (123). Da Text nicht summiert werden kann, ist das Ergebnis der Summe 0, und es wird stattdessen die Anzahl (Count) verwendet.
Die Lösung (Minimal und Robust)
Wir müssen Pandas anweisen, die Datentypen aggressiver zu interpretieren, bevor die Daten für die JSON-Ausgabe vorbereitet werden.
Wir führen eine neue Hilfsfunktion optimize_dataframe_types ein. Diese verwendet pd.to_numeric(..., errors='coerce'). Dies weist Pandas an, die Konvertierung zu versuchen. Werte, die nicht konvertiert werden können (z.B. echter Text), werden zu NaN (Not a Number), was für die Analyse korrekt ist.
Diese Änderung betrifft nur die Datei datafiles/views.py und löst das Problem für alle Dateitypen (Excel, CSV, Pickle).
Aktualisierter Code: datafiles/views.py
Bitte ersetzen Sie Ihre datafiles/views.py durch den folgenden Code.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DataFile
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.contrib import messages
import pandas as pd
import io
import logging
import chardet
import numpy as np

logger = logging.getLogger(__name__)

# NEU: Hilfsfunktion zur intelligenten Typ-Optimierung
def optimize_dataframe_types(df):
    """
    Versucht, die Datentypen der Spalten intelligent zu konvertieren, insbesondere Text zu Zahlen.
    Dies ist notwendig, da Pandas bei gemischten Daten oft alles als Text (object) einliest.
    """
    for col in df.columns:
        # Nur Spalten vom Typ 'object' (Text) betrachten
        if pd.api.types.is_object_dtype(df[col]):
            try:
                # Versuch, die Spalte zu numerisch zu konvertieren.
                # errors='coerce' wandelt nicht konvertierbare Werte in NaN um.
                converted_series = pd.to_numeric(df[col], errors='coerce')
                
                # Heuristik: Wir übernehmen die Konvertierung nur, wenn sie sinnvoll war.
                # Wenn die Spalte nicht komplett zu NaN wurde (d.h. mindestens eine Zahl erkannt wurde),
                # akzeptieren wir die neue numerische Spalte. (Es sei denn, die Spalte war vorher schon leer).
                if not converted_series.isnull().all() or df[col].isnull().all():
                    df[col] = converted_series
                    logger.debug(f"Spalte '{col}' erfolgreich zu numerischem Typ konvertiert.")
            except Exception as e:
                # Sicherstellen, dass Fehler beim Konvertieren nicht die App abstürzen lassen
                logger.debug(f"Konnte Spalte {col} nicht zu numerisch konvertieren: {e}")
    return df


@login_required
def download_file(request, file_id):
    # (Keine Änderungen in dieser Funktion)
    try:
        f = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        if DataFile.objects.filter(pk=file_id).exists():
            logger.warning(f"User {request.user.id} tried to access file {file_id} without permission.")
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    if not f.file or not f.file.storage.exists(f.file.name):
        logger.error(f"File {file_id} exists in DB but not in storage: {f.file.name}")
        raise Http404("Datei nicht im Speicher vorhanden.")

    try:
        return FileResponse(f.file.open('rb'), as_attachment=True, filename=f.filename())
    except Exception as e:
        logger.error(f"Error serving file {file_id}: {e}")
        messages.error(request, "Beim Herunterladen der Datei ist ein Fehler aufgetreten.")
        return redirect('dashboard')


@login_required
def analyze_file(request, file_id):
    # (Sicherheitschecks unverändert)
    try:
        data_file = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        if DataFile.objects.filter(pk=file_id).exists():
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    if not data_file.is_analyzable():
         messages.warning(request, f"Dieser Dateityp ({data_file.get_file_extension()}) kann nicht online analysiert werden (nur CSV/Excel/Pickle).")
         return redirect('dashboard')

    if not data_file.file.storage.exists(data_file.file.name):
        raise Http404("Datei nicht im Speicher vorhanden.")

    # Datei mit Pandas lesen
    try:
        file_content = data_file.file.read()
        extension = data_file.get_file_extension()

        sheet_names = None
        selected_sheet = None
        df = pd.DataFrame()

        # (Logik zum Lesen von CSV/Excel/Pickle unverändert)
        if extension == '.csv':
            df = read_csv_robust(file_content)

        elif extension in ['.xlsx', '.xls', '.xlsm']:
            with io.BytesIO(file_content) as bio:
                try:
                    # Pandas die Engine wählen lassen
                    xls = pd.ExcelFile(bio)
                except Exception as e:
                     raise ValueError(f"Konnte Excel-Datei nicht lesen (verschlüsselt oder korrupt?): {e}")
                
                sheet_names = xls.sheet_names or []
                selected_sheet = request.GET.get('sheet') or (sheet_names[0] if sheet_names else None)
                if selected_sheet not in sheet_names and sheet_names:
                    selected_sheet = sheet_names[0]
                df = xls.parse(selected_sheet) if selected_sheet else pd.DataFrame()

        elif extension == '.pkl':
            df = pd.read_pickle(io.BytesIO(file_content))

        # *** Cleaning & Robustheit ***
        if not df.empty:
            # (Cleaning von leeren Zeilen/Spaltennamen unverändert)
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)

            def _safe_colname(idx, col):
                s = '' if col is None else str(col).strip()
                # Auch "Unnamed: X" aus Excel abfangen
                if s.startswith('Unnamed:'):
                     return f'Spalte_{idx+1}'
                return s if s not in ('', 'nan', 'NaN', 'None') else f'Spalte_{idx+1}'
            
            # Sicherstellen, dass Spaltennamen einzigartig sind
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

            # >>> WICHTIGE ÄNDERUNG HIER <<<
            # Wende die Typ-Optimierung an, um Zahlen korrekt zu erkennen
            df = optimize_dataframe_types(df)

        # Datenbereinigung und Konvertierung für JSON-Kompatibilität
        # Diese Funktion profitiert nun von den korrekt erkannten numerischen Typen.
        df = prepare_dataframe_for_json(df)

        # DataFrame in JSON konvertieren.
        data_json = df.to_json(orient='records', date_format='iso', force_ascii=False)

    except ValueError as e:
        logger.error(f"Fehler beim Bestimmen des CSV-/Excel-Formats für Datei {file_id}: {e}")
        messages.error(request, f"Fehler beim Lesen der Datei: {e}")
        return redirect('dashboard')
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Analysieren der Datei {file_id}: {e}", exc_info=True)
        messages.error(request, f"Ein unerwarteter Fehler ist aufgetreten beim Verarbeiten der Datei: {type(e).__name__}")
        return redirect('dashboard')

    return render(request, 'datafiles/analyze.html', {
        'data_file': data_file,
        'data_json': data_json,
        'sheet_names': sheet_names or [],
        'selected_sheet': selected_sheet,
    })


def prepare_dataframe_for_json(df):
    """Bereinigt DataFrame-Typen für eine sichere JSON-Serialisierung."""
    
    # NaN/Null-Werte behandeln (Ersetzen durch None, was in JSON zu null wird).
    # Dies fängt auch die NaNs ab, die durch optimize_dataframe_types entstanden sind.
    df = df.replace({np.nan: None})

    # Konvertieren von Spaltentypen
    for col in df.columns:
        # Behandeln von Datetime-Objekten
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').replace('NaT', None)
        
        # Behandeln von numerischen Typen (jetzt korrekt erkannt dank optimize_dataframe_types)
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace([np.inf, -np.inf], None)
            
            # Konvertieren zu Standard-Python-Typen (int oder float).
            # Dies stellt sicher, dass die Zahlen im JSON *nicht* in Anführungszeichen stehen.
            df[col] = df[col].apply(lambda x: x if x is None else (int(x) if isinstance(x, float) and x.is_integer() else float(x)))

        # Behandeln von Objekten (Text)
        elif pd.api.types.is_object_dtype(df[col]):
             df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
             
    return df


def read_csv_robust(file_content_bytes):
    # (Keine Änderungen in dieser Funktion)
    """Hilfsfunktion zum Lesen von CSVs mit automatischem Encoding und Separator Sniffing."""
    detection = chardet.detect(file_content_bytes[:102400]) 
    encoding = detection.get('encoding')
    if not encoding: encoding = 'utf-8'

    separators = [',', ';', '\t', '|']
    best_df = None
    max_cols = 0
    # Erstelle eine Liste von Encodings zum Testen, ohne Duplikate
    encodings_to_try = list(dict.fromkeys(filter(None, [encoding, 'utf-8', 'latin1'])))

    for enc in encodings_to_try:
        try:
            decoded_content = file_content_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
        for separator in separators:
            try:
                df = pd.read_csv(io.StringIO(decoded_content), sep=separator, engine='python')
                num_cols = len(df.columns)
                if num_cols > max_cols:
                    max_cols = num_cols
                    best_df = df
                if num_cols > 1: return df
            except Exception:
                continue
    if best_df is not None: return best_df
    raise ValueError("Konnte das CSV-Format (Encoding/Separator) nicht zuverlässig bestimmen.")


