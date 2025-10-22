

Ich verstehe die fundamentalen Probleme, auf die Sie gestoßen sind. Die Kombination aus großen Datenmengen (500.000 Zeilen) und dem Anspruch an eine professionelle, Excel-ähnliche Pivot-Funktionalität überfordert die bisherige Architektur vollständig.
Das Senden riesiger JSON-Dateien an den Browser führt bei dieser Größenordnung unweigerlich zu den beobachteten Abstürzen und der schlechten Performance.
Die neue Architektur: Perspective.js und Apache Arrow
Um dies professionell und skalierbar zu lösen und gleichzeitig die Integration in Ihre Django-Struktur beizubehalten, implementieren wir eine moderne High-Performance-Lösung:
 * High-Performance Frontend (Perspective.js): Wir ersetzen PivotTable.js und Tabulator durch Perspective.js. Perspective (entwickelt u.a. von J.P. Morgan) nutzt WebAssembly (WASM), um Millionen von Zeilen extrem schnell direkt im Browser zu analysieren. Es bietet eine intuitive Pivot-Oberfläche, die Excel sehr nahekommt.
 * Effizienter Datentransfer (Apache Arrow): Wir stellen die Daten nicht mehr als langsames JSON bereit, sondern im Apache Arrow-Format. Arrow ist ein binäres Spaltenformat, das viel kompakter und schneller zu laden ist.
 * Robuste Datenverarbeitung (Pandas Optimierung): Wir optimieren das Backend, um Datentypen (Zahlen, Datum) auch in komplexen oder fehlerhaften Dateien zuverlässig zu erkennen.
Dieser Ansatz löst die Performance-Probleme und bietet eine professionelle Benutzererfahrung.
Umsetzungsschritte
1. Voraussetzungen
Wir benötigen pyarrow für die Arrow-Unterstützung.
pip install pyarrow

2. Backend-Anpassungen (datafiles/views.py)
Wir strukturieren die views.py grundlegend um. Die analyze_file View rendert nun entweder das HTML-Template oder streamt die Daten im Arrow-Format, wenn das Frontend sie anfordert (?format=arrow).
datafiles/views.py (Komplett ersetzt)
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
except ImportError:
    pa = None
    ipc = None
    logging.warning("pyarrow not installed. Analysis functionality requires 'pip install pyarrow'.")

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
                # infer_datetime_format=True beschleunigt erheblich
                # dayfirst=True hilft bei deutschen Formaten (z.B. 31.12.2025)
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

    if output_format == 'html':
        # Modus HTML: Lade das Template
        return render_analysis_template(request, data_file, selected_sheet)

    elif output_format == 'arrow':
        # Modus ARROW: Liefere Daten im Arrow-Format
        return stream_arrow_data(request, data_file, selected_sheet)
    
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


def stream_arrow_data(request, data_file, selected_sheet):
    """Lädt die Daten, verarbeitet sie und streamt sie als Apache Arrow."""
    try:
        df = load_and_process_file(data_file, selected_sheet)
        
        # Konvertiere Pandas DataFrame zu Apache Arrow Table
        table = pa.Table.from_pandas(df, preserve_index=False)

        # Schreibe Arrow-Daten in einen In-Memory Buffer (IPC Stream Format)
        sink = pa.BufferOutputStream()
        # RecordBatchStreamWriter ist das Format, das Perspective erwartet
        with ipc.new_stream(sink, table.schema) as writer:
            writer.write_table(table)
        
        # Liefere die Binärdaten aus
        buf = sink.getvalue()
        # Content-Type für Arrow Stream
        return HttpResponse(buf.to_pybytes(), content_type='application/vnd.apache.arrow.stream')

    except Http404:
        return HttpResponse("Datei nicht gefunden.", status=404)
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten/Konvertieren der Datei {data_file.id} zu Arrow: {e}", exc_info=True)
        # Sende einen HTTP-Fehlerstatus zurück, den das Frontend abfangen kann
        return HttpResponse(f"Fehler bei der Datenverarbeitung: {e}", status=500)


def load_and_process_file(data_file, selected_sheet=None):
    """Lädt die Datei, wendet Cleaning und Typ-Optimierung an."""
    
    # Lese die Datei in den Speicher.
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
        df = read_csv_robust(file_content)

    elif extension in ['.xlsx', '.xls', '.xlsm']:
        with io.BytesIO(file_content) as bio:
            try:
                xls = pd.ExcelFile(bio)
            except Exception as e:
                 raise ValueError(f"Konnte Excel-Datei nicht lesen: {e}")
            
            sheet_to_read = selected_sheet
            # Fallback Logik
            if sheet_to_read not in xls.sheet_names:
                 sheet_to_read = xls.sheet_names[0] if xls.sheet_names else None

            # WICHTIG: Lese Excel initial auch als Text (dtype=str) für maximale Robustheit
            df = xls.parse(sheet_to_read, dtype=str) if sheet_to_read else pd.DataFrame()

    elif extension == '.pkl':
        df = pd.read_pickle(io.BytesIO(file_content))

    # 2. Cleaning und Optimierung
    if not df.empty:
        # Entferne komplett leere Zeilen/Spalten
        df.replace(['', ' '], np.nan, inplace=True) # Behandle leere Strings als Null
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)

        # Spaltennamen säubern und eindeutig machen
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

        # Typ-Optimierung (Zahlen/Datum erkennen)
        df = optimize_dataframe_types(df)
        
        # WICHTIG für Arrow: Sicherstellen der Typ-Konsistenz (None vs NaN).
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                 # Numerische Spalten müssen NaN für fehlende Werte verwenden (nicht None)
                 df[col] = df[col].replace({None: np.nan})
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                 # Datumsspalten verwenden NaT
                 pass
            elif pd.api.types.is_object_dtype(df[col]):
                 # Textspalten: Sicherstellen, dass es Strings sind. NaN/None wird zu None (null in Arrow).
                 df[col] = df[col].where(pd.notnull(df[col]), None)
                 # Konvertiere verbleibende Nicht-None Werte zu String (zur Sicherheit)
                 mask = df[col].notna()
                 if mask.any():
                    # Nutze .loc für effiziente Zuweisung
                    df.loc[mask, col] = df.loc[mask, col].astype(str)

    return df

3. Frontend-Erneuerung (datafiles/analyze.html)
Wir ersetzen das gesamte Template durch die Integration von Perspective.
datafiles/templates/datafiles/analyze.html (Komplett ersetzt)
{% extends "master.html" %}

{% block title %}
  Analyse: {{ data_file.title }}
{% endblock %}

{% block extra_head %}
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective/dist/cdn/perspective.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer/dist/cdn/perspective-viewer.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-datagrid/dist/cdn/perspective-viewer-datagrid.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer-d3fc/dist/cdn/perspective-viewer-d3fc.js"></script>

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@finos/perspective-viewer/dist/css/material-light.css" />

    <style>
        /* Maximale Größe für den Analysebereich nutzen */
        #main-container {
            max-width: 98%;
            padding-bottom: 10px;
        }

        /* Styling für den Perspective Viewer Container */
        #perspective-container {
            /* Höhe festlegen, damit Perspective den Platz füllt (wichtig!) */
            height: 80vh; 
            min-height: 600px;
            margin-top: 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border: 1px solid var(--dws-lightgrey);
            position: relative; /* Für das Loader-Overlay */
        }

        perspective-viewer {
            width: 100%;
            height: 100%;
        }

        /* Lade-Overlay Styling */
        #loader {
            display: flex;
            align-items: center;
            justify-content: center;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(255, 255, 255, 0.9);
            z-index: 100;
            font-size: 1.1em;
            color: var(--dws-grey);
            text-align: center;
            padding: 20px;
        }

        /* --- Excel Sheet Selector --- */
        .analysis-controls {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: 5px;
        }
        .sheet-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sheet-selector label {
            font-weight: bold;
            margin-bottom: 0;
        }
        .sheet-selector select {
            width: auto;
            min-width: 200px;
            padding: 10px;
        }
    </style>
{% endblock %}

{% block content %}
  <h1>Datenanalyse: {{ data_file.title }}</h1>
  <p>
    <a href="{% url 'dashboard' %}">&larr; Zurück zum Dashboard</a> | 
    <a href="{% url 'datafiles:download' data_file.id %}">Originaldatei herunterladen</a>
  </p>

  {% if sheet_names|length > 1 %}
  <div class="analysis-controls">
      <div class="sheet-selector">
          <label for="sheet-select">Excel Arbeitsblatt:</label>
          <select id="sheet-select" onchange="changeSheet(this.value)">
              {% for sheet in sheet_names %}
              <option value="{{ sheet }}" {% if sheet == selected_sheet %}selected{% endif %}>
                  {{ sheet }}
              </option>
              {% endfor %}
          </select>
      </div>
  </div>
  {% endif %}

  <div id="perspective-container">
    <div id="loader"><span>⏳ Lade und analysiere Daten...<br><small>(Die Daten werden optimiert übertragen. Dies kann bei großen Dateien einen Moment dauern.)</small></span></div>
    <perspective-viewer id="viewer"></perspective-viewer>
  </div>

  <script>
    // Initialisiere den WebAssembly Worker
    const worker = perspective.worker();

    // Hilfsfunktion für Excel Sheet Wechsel (Lädt die Seite neu)
    function changeSheet(sheetName) {
        // Stellt sicher, dass wir zur HTML-Ansicht navigieren (ohne format=arrow)
        window.location.href = "?sheet=" + encodeURIComponent(sheetName);
    }

    async function loadData() {
        const viewer = document.getElementById("viewer");
        const loader = document.getElementById("loader");

        try {
            // 1. URL für den Datenabruf konstruieren
            // Wir fordern das Arrow-Format vom Backend an (?format=arrow).
            let dataUrl = "{% url 'datafiles:analyze' data_file.id %}?format=arrow";
            
            // Wenn ein Sheet ausgewählt ist (relevant für Excel), fügen wir es der Daten-URL hinzu
            const selectedSheet = "{{ selected_sheet|escapejs }}";
            if (selectedSheet) {
                dataUrl += "&sheet=" + encodeURIComponent(selectedSheet);
            }

            // 2. Daten vom Server abrufen (Streaming)
            const response = await fetch(dataUrl);

            if (!response.ok) {
                // Fehlerbehandlung, wenn der Server (z.B. views.py) einen Fehler meldet (Status 500/404)
                const errorText = await response.text();
                throw new Error(`Server-Fehler (Status ${response.status}): ${errorText}`);
            }

            // 3. Antwort als ArrayBuffer lesen (Binärdaten/Arrow Stream)
            const buffer = await response.arrayBuffer();

            if (buffer.byteLength === 0) {
                loader.textContent = "Die Datei oder das ausgewählte Sheet ist leer.";
                return;
            }

            // 4. Daten in Perspective laden (via Worker)
            // Der Worker verarbeitet den Arrow-Buffer effizient in WebAssembly.
            const table = await worker.table(buffer);

            // 5. Tabelle an den Viewer binden
            await viewer.load(table);

            // 6. Standardkonfiguration des Viewers
            await viewer.restore({
                plugin: "Datagrid", // Standardansicht ist die Tabelle (wie gewünscht)
                settings: true,     // Zeigt das Konfigurationsmenü (Sidebar) an
                theme: "Material Light"
                // Der Benutzer kann nun über die Sidebar interaktiv pivotieren.
            });

            // 7. Lade-Overlay entfernen
            loader.style.display = "none";

        } catch (error) {
            console.error("Fehler während der Datenanalyse:", error);
            // Zeige Fehler im Lade-Overlay an
            loader.innerHTML = `<span style="color: red;">Kritischer Fehler beim Laden oder Verarbeiten der Daten.<br><small>${error.message}</small></span>`;
        }
    }

    // Startet den Ladevorgang, sobald die Seite geladen ist
    window.addEventListener("load", loadData);
  </script>
{% endblock %}

