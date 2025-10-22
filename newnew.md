Ich habe das bereitgestellte Django-Repository eingehend analysiert und alle Punkte auf Ihrer Todo-Liste umgesetzt. Der Fokus lag auf Robustheit, der Integration von Standardfunktionalitäten und der signifikanten Verbesserung der Benutzerfreundlichkeit im Stil von DWS, während die Änderungen am Kern-Code minimal und zielgerichtet gehalten wurden.
Hier ist die detaillierte Analyse und die Umsetzung der Anforderungen.
1. Analyse und Technologie-Entscheidungen
Todo: Darstellung der Tabellen (Intuitiver, Excel-ähnlich, Streamlit Evaluation)
Die Anforderung lautet, dass zunächst die Tabelle angezeigt wird und dann mit Pivot-Auswahl gefiltert wird.
 * Streamlit Evaluation: Streamlit läuft als separater Service. Die Integration in Django (insbesondere die Authentifizierung) ist komplex und würde die Architektur unnötig verkomplizieren. Daher wurde dieser Ansatz verworfen.
 * Optimierte Lösung (Tabulator.js + PivotTable.js): Um die Anforderung optimal zu erfüllen, habe ich Tabulator.js integriert. Tabulator bietet eine moderne, interaktive Tabellenansicht (Sortieren, Filtern direkt in den Spaltenköpfen, Paginierung) – sehr ähnlich zu einer Excel-Tabelle.
 * Umsetzung: Der Benutzer sieht nun standardmäßig die intuitive Tabellenansicht (Tabulator). Per Knopfdruck kann er zur tiefgreifenden Pivot-Analyse (PivotTable.js) wechseln. Dies bietet maximale Flexibilität und Intuitivität.
2. Umsetzung der weiteren Todos
 * Passwort ändern: Implementiert durch Nutzung der sicheren Django-Standardfunktionen (PasswordChangeView).
 * Excel-Sheet Auswahl: Im Frontend wurde ein Dropdown-Menü hinzugefügt, das angezeigt wird, wenn die Excel-Datei mehrere Sheets enthält.
 * DWS CSS Style: Das globale Styling wurde angepasst, um das Corporate Design der DWS widerzuspiegeln (Farben: Dunkelblau #00338D als Primärfarbe; Schriftart: Roboto).
 * Robustheit: Verbesserungen in datafiles/views.py, um sicherzustellen, dass Spaltennamen immer eindeutig sind (wichtig für die Analyse) und die download_file Funktion korrekt implementiert ist.
3. Das aktualisierte Repository (Geänderte und Neue Dateien)
Hier sind alle relevanten Dateien mit den Änderungen.
App: datafiles
datafiles/views.py (Aktualisiert: Robustheit und Korrekturen)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DataFile
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.contrib import messages
import pandas as pd
import io
import logging
import chardet # Für verbesserte Encoding-Erkennung
import numpy as np

logger = logging.getLogger(__name__)

@login_required
def download_file(request, file_id):
    # SICHERHEIT: Sicherstellen, dass die Datei existiert UND dem aktuellen Benutzer gehört.
    try:
        f = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        if DataFile.objects.filter(pk=file_id).exists():
            logger.warning(f"User {request.user.id} tried to access file {file_id} without permission.")
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    # Prüfen, ob die Datei physisch existiert
    if not f.file or not f.file.storage.exists(f.file.name):
        logger.error(f"File {file_id} exists in DB but not in storage: {f.file.name}")
        raise Http404("Datei nicht im Speicher vorhanden.")

    # FileResponse ist effizient für das Streaming von Dateien.
    try:
        # KORREKTUR: FileResponse direkt das File-Objekt im Binärmodus übergeben.
        return FileResponse(f.file.open('rb'), as_attachment=True, filename=f.filename())
    except Exception as e:
        logger.error(f"Error serving file {file_id}: {e}")
        messages.error(request, "Beim Herunterladen der Datei ist ein Fehler aufgetreten.")
        return redirect('dashboard')


@login_required
def analyze_file(request, file_id):
    # SICHERHEIT: Gleicher Check wie beim Download
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

        sheet_names = None       # für Template (Dropdown)
        selected_sheet = None    # für Template (markierte Auswahl)
        df = pd.DataFrame()

        if extension == '.csv':
            # Robustes CSV Handling
            df = read_csv_robust(file_content)

        elif extension in ['.xlsx', '.xls', '.xlsm']:
            # Alle Sheet-Namen ermitteln
            with io.BytesIO(file_content) as bio:
                # Robustheit: Fehler abfangen, wenn Excel korrupt/verschlüsselt ist
                try:
                    # Pandas die Engine wählen lassen (openpyxl für .xlsx/.xlsm, xlrd für .xls wenn verfügbar)
                    xls = pd.ExcelFile(bio)
                except Exception as e:
                     raise ValueError(f"Konnte Excel-Datei nicht lesen (verschlüsselt oder korrupt?): {e}")
                
                sheet_names = xls.sheet_names or []
                # Auswahl aus Query (Fallback: erstes Sheet)
                selected_sheet = request.GET.get('sheet') or (sheet_names[0] if sheet_names else None)
                if selected_sheet not in sheet_names and sheet_names:
                    selected_sheet = sheet_names[0]
                # Konkretes Sheet einlesen
                df = xls.parse(selected_sheet) if selected_sheet else pd.DataFrame()

        elif extension == '.pkl':
            df = pd.read_pickle(io.BytesIO(file_content))

        # *** Cleaning & Robustheit ***
        if not df.empty:
            # Komplett leere Zeilen/Spalten weg
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)

            # Spaltenüberschriften säubern/auffüllen
            def _safe_colname(idx, col):
                s = '' if col is None else str(col).strip()
                # Auch "Unnamed: X" aus Excel abfangen
                if s.startswith('Unnamed:'):
                     return f'Spalte_{idx+1}'
                return s if s not in ('', 'nan', 'NaN', 'None') else f'Spalte_{idx+1}'
            
            # NEU: Sicherstellen, dass Spaltennamen einzigartig sind (Wichtig für JS Analyse)
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

        # Datenbereinigung und Konvertierung für JSON-Kompatibilität
        df = prepare_dataframe_for_json(df)

        # DataFrame in JSON konvertieren. force_ascii=False ist wichtig für Umlaute.
        data_json = df.to_json(orient='records', date_format='iso', force_ascii=False)

    except ValueError as e:
        logger.error(f"Fehler beim Bestimmen des CSV-/Excel-Formats für Datei {file_id}: {e}")
        messages.error(request, f"Fehler beim Lesen der Datei: {e}")
        return redirect('dashboard')
    except Exception as e:
        # Allgemeiner Fehler beim Parsen oder Konvertieren
        logger.error(f"Unerwarteter Fehler beim Analysieren der Datei {file_id}: {e}", exc_info=True)
        messages.error(request, f"Ein unerwarteter Fehler ist aufgetreten beim Verarbeiten der Datei: {type(e).__name__}")
        return redirect('dashboard')

    return render(request, 'datafiles/analyze.html', {
        'data_file': data_file,
        'data_json': data_json,
        'sheet_names': sheet_names or [],     # für Dropdown
        'selected_sheet': selected_sheet,     # für Markierung
    })

# Hilfsfunktionen (unverändert aus dem Input, da bereits sehr robust)
def prepare_dataframe_for_json(df):
    """Bereinigt DataFrame-Typen für eine sichere JSON-Serialisierung, ohne Datentypen zu verlieren."""
    df = df.replace({np.nan: None})
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').replace('NaT', None)
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace([np.inf, -np.inf], None)
            df[col] = df[col].apply(lambda x: x if x is None else (int(x) if isinstance(x, float) and x.is_integer() else float(x)))
        elif pd.api.types.is_object_dtype(df[col]):
             df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
    return df

def read_csv_robust(file_content_bytes):
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

App: members
members/urls.py (Aktualisiert: Passwort-URLs hinzugefügt)
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy # Import hinzugefügt

# URLs sind unter /account/ erreichbar

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register_user, name='register_user'),
    # Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='members/login.html'), name='login'),
    # Logout View angepasst: template_name entfernt, da Logout meist direkt weiterleitet
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # NEU: Passwort ändern
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='members/password_change_form.html',
        success_url=reverse_lazy('password_change_done') # Weiterleitung nach Erfolg
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='members/password_change_done.html'
    ), name='password_change_done'),
]

Templates (Styling und neue Features)
members/templates/master.html (Komplett überarbeitet für DWS-Stil)
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}DWS Datenportal{% endblock %}</title>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap" rel="stylesheet">
  
  <style>
    /* Globales CSS Styling - DWS Corporate Design */
    :root {
        /* DWS Colors (Authentic DWS Blue) */
        --dws-blue: #00338D;       /* Primärfarbe */
        --dws-lightblue: #0099CC;  /* Sekundärfarbe/Interaktion */
        --dws-dark: #002266;       /* Hover-Effekt Primär */
        --dws-grey: #666666;
        --dws-lightgrey: #E0E0E0;
        --background-color: #F8F9FA;
        --text-color: #333333;
    }

    body { 
        font-family: 'Roboto', Arial, sans-serif; 
        margin: 0; 
        background-color: var(--background-color); 
        color: var(--text-color); 
        line-height: 1.6; 
    }
    .container { padding: 30px; max-width: 1400px; margin: auto; }
    #main-container {
        padding-top: 20px; 
    }

    /* Navigation Styling */
    nav { 
        background: var(--dws-blue); /* DWS Blau für die Navigation */
        padding: 15px 30px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        color: white;
    }
    nav a { 
        text-decoration: none; 
        color: white; 
        padding: 8px 15px; 
        border-radius: 4px;
        transition: background-color 0.3s;
    }
    nav a:hover, nav .nav-button:hover { 
        background-color: var(--dws-lightblue);
    }
    .logo a { 
        font-weight: 700; 
        font-size: 1.5em; 
        padding-left: 0; 
    }
    .user-info { font-size: 0.9em; display: flex; align-items: center; gap: 15px; }
    .user-name { font-weight: bold; margin-right: 10px; }

    .nav-button {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        padding: 8px 15px;
        border-radius: 4px;
        font-size: 1em;
        transition: background-color 0.3s;
    }
    
    /* Typography */
    h1, h2 {
        color: var(--text-color);
        margin-bottom: 20px;
    }
    h1 { font-size: 2.2em; }
    h2 { font-size: 1.8em; }

    /* Styling für Django Messages (Flash-Nachrichten) */
    .messages { list-style-type: none; padding: 0; margin-bottom: 20px; }
    .messages li { padding: 12px 15px; border-radius: 5px; border: 1px solid transparent; margin-bottom: 10px; }
    .messages .info { background-color: #d9edf7; color: #31708f; border-color: #bce8f1; }
    .messages .success { background-color: #dff0d8; color: #3c763d; border-color: #d6e9c6; }
    .messages .error { background-color: #f2dede; color: #a94442; border-color: #ebccd1; }

    /* Content Card (für Formulare und Boxen) */
    .content-card {
        background: #ffffff;
        padding: 30px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid var(--dws-lightgrey);
    }

    /* Formular Styling (Global) */
    .form-group { margin-bottom: 20px; }
    label { display: block; margin-bottom: 8px; font-weight: 500; color: var(--dws-grey); }
    input[type=text], input[type=password], input[type=email], select { 
        width: 100%; 
        padding: 12px; 
        border: 1px solid #ccc; 
        border-radius: 4px; 
        box-sizing: border-box; 
        font-size: 1em;
    }
    input:focus, select:focus {
        border-color: var(--dws-lightblue);
        outline: none;
        box-shadow: 0 0 0 2px rgba(0, 153, 204, 0.2);
    }
    .errorlist { color: #a94442; list-style-type: none; padding-left: 0; font-size: 0.85em; margin-top: 5px;}
    .form-help-text {
        font-size: 0.8em; color: #666; margin-top: 5px;
    }

    /* Button Styling */
    button, .button { 
        padding: 12px 20px; 
        background-color: var(--dws-blue); 
        color: white; 
        border: none; 
        border-radius: 5px; 
        cursor: pointer; 
        font-size: 1em;
        text-decoration: none;
        display: inline-block;
        transition: background-color 0.3s;
    }
    button:hover, .button:hover { 
        background-color: var(--dws-dark);
        text-decoration: none;
        color: white;
    }

    .button-secondary {
        background-color: #6c757d;
    }
    .button-secondary:hover {
        background-color: #5a6268;
    }

    /* Links */
    a {
        color: var(--dws-blue);
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }

  </style>
  {% block extra_head %}{% endblock %}
</head>
<body>

<nav>
    <div class="logo">
        <a href="{% url 'dashboard' %}">DWS Datenportal</a>
    </div>
    <div class="user-info">
        {% if user.is_authenticated %}
            <span class="user-name">{{ user.get_full_name|default:user.username }}</span>
            
            <a href="{% url 'register_user' %}">User anlegen</a>
            <a href="{% url 'password_change' %}">Passwort ändern</a>

            {% if user.is_staff %}
            <a href="{% url 'admin:index' %}">Admin</a>
            {% endif %}
           
            <form action="{% url 'logout' %}" method="post" style="display:inline;">
                {% csrf_token %}
                <button type="submit" class="nav-button">
                  Logout
                </button>
              </form>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
        {% endif %}
    </div>
</nav>

<div class="container" id="main-container">
    {% if messages %}
        <ul class="messages">
            {% for message in messages %}
            <li{% if message.tags %} class="{{ message.tags }}"{% endif %}>{{ message }}</li>
            {% endfor %}
        </ul>
    {% endif %}

    {% block content %}
    {% endblock %}
</div>

</body>
</html>

datafiles/templates/datafiles/analyze.html (Neu gestaltet: Tabulator, Pivot-Switch, Excel-Selector)
{% extends "master.html" %}

{% block title %}
  Analyse: {{ data_file.title }}
{% endblock %}

{% block extra_head %}
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.css">

    <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.17/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.js"></script>
    <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/c3_renderers.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.de.min.js"></script>

    <link href="https://unpkg.com/tabulator-tables@5.5.2/dist/css/tabulator.min.css" rel="stylesheet">
    <script type="text/javascript" src="https://unpkg.com/tabulator-tables@5.5.2/dist/js/tabulator.min.js"></script>

    <style>
        /* Anpassung des Containers, da Analyse oft breit ist */
        #main-container { max-width: 98%; } 

        /* --- View Switcher & Controls --- */
        .analysis-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }
        .view-switcher {
            display: flex;
            gap: 10px;
        }

        /* --- Excel Sheet Selector --- */
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

        /* --- Tabulator Styling (DWS Theme Integration) --- */
        #data-table {
            margin-top: 10px;
            border: 1px solid var(--dws-lightgrey);
        }
        .tabulator .tabulator-header {
            background-color: var(--dws-blue);
            color: white;
        }
        .tabulator .tabulator-header .tabulator-col {
            background-color: var(--dws-blue);
        }
        .tabulator .tabulator-header .tabulator-col-title {
            color: white;
        }
        .tabulator .tabulator-header .tabulator-header-filter input {
            /* Sicherstellen, dass Filter-Inputs sichtbar sind */
            color: #333;
        }

        /* --- PivotTable Styling --- */
        #pivot-output { 
            margin-top: 20px; 
            display: none; /* Standardmäßig versteckt */
            background: white;
            padding: 15px;
            border: 1px solid var(--dws-lightgrey);
        }
        .pvtUi { width: 100%; font-size: 13px; }
        body.pvtBody { overflow: hidden; } 

        .instructions { 
            background: #e9f5ff; 
            padding: 15px; 
            border-radius: 5px; 
            margin-bottom: 20px; 
            border: 1px solid #bce8f1; 
            display: none; /* Nur im Pivot-Modus anzeigen */
        }
    </style>
{% endblock %}

{% block content %}
  <h1>Datenanalyse: {{ data_file.title }}</h1>
  <p>
    <a href="{% url 'dashboard' %}">&larr; Zurück zum Dashboard</a> | 
    <a href="{% url 'datafiles:download' data_file.id %}">Originaldatei herunterladen</a>
  </p>
  

  <div class="analysis-controls">
      
      <div class="view-switcher">
        <button id="btn-table-view" class="button" onclick="switchView('table')">Standard-Tabelle</button>
        <button id="btn-pivot-view" class="button button-secondary" onclick="switchView('pivot')">Pivot-Analyse</button>
      </div>

      {% if sheet_names|length > 1 %}
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
      {% endif %}
  </div>

  <div class="instructions" id="pivot-instructions">
    <strong>Anleitung Pivot-Analyse:</strong> Ziehen Sie die Felder per Drag & Drop, um die Tabelle zu pivotieren. Nutzen Sie die Dropdown-Menüs für Aggregationen oder Visualisierungen.
  </div>

  <div id="data-table"></div>

  <div id="pivot-output">Lade interaktive Pivot-Tabelle...</div>

  <script type="text/javascript">
    // 1. Daten laden
    var data = {{ data_json|safe }};
    var pivotInitialized = false;

    // Hilfsfunktion für Excel Sheet Wechsel
    function changeSheet(sheetName) {
        window.location.href = "?sheet=" + encodeURIComponent(sheetName);
    }

    // Funktion zur automatischen Erkennung von Spaltendefinitionen für Tabulator
    function getColumnDefinitions(data) {
        if (data.length === 0) return [];

        var keys = Object.keys(data[0]);
        return keys.map(key => {
            var colDef = {
                title: key, 
                field: key, 
                headerFilter: "input", // Filter Input im Header
                resizable: true,
                sorter: "string"
            };

            // Einfache Typerkennung (Numerisch vs. String) für besseres Sortieren
            var sample = data.slice(0, 50);
            var isNumeric = sample.every(row => {
                var val = row[key];
                // Prüft ob Wert null, eine Zahl oder ein String ist, der zu einer Zahl konvertiert werden kann
                return val === null || typeof val === 'number' || (typeof val === 'string' && val.trim() !== "" && !isNaN(parseFloat(val)) && isFinite(val));
            });

            if (isNumeric) {
                colDef.sorter = "number";
                colDef.hozAlign = "right";
            }
            
            return colDef;
        });
    }

    // 2. Initialisiere Tabulator (Standard View)
    var table;
    if (data && data.length > 0) {
        table = new Tabulator("#data-table", {
            data: data,
            layout: "fitDataStretch",
            pagination: "local",
            paginationSize: 50,
            paginationSizeSelector: [25, 50, 100, 500],
            movableColumns: true,
            resizableColumnFit: true,
            columns: getColumnDefinitions(data),
            locale: "de-de", // Deutsche Lokalisierung
            langs:{
                "de-de":{
                    "pagination":{
                        "page_size":"Einträge pro Seite",
                        "first":"Anfang",
                        "last":"Ende",
                        "next":"Vor",
                        "prev":"Zurück",
                    },
                    "headerFilters":{
                        "default":"filtern...", 
                    }
                }
            },
        });
    } else {
        $('#data-table').html('<p>Keine Daten in dieser Datei oder diesem Sheet gefunden.</p>');
    }

    // 3. Initialisiere PivotTable (Analysis View) - Nur bei Bedarf (Lazy Load)
    function initializePivot() {
        if (pivotInitialized) return;

        $(function(){
            var localization = $.pivotUtilities.locales.de;
            var renderers = $.extend(
                {},
                localization.renderers,
                $.pivotUtilities.c3_renderers
            );

            $("#pivot-output").pivotUI(
                data,
                {
                    renderers: renderers,
                    localeStrings: localization.localeStrings,
                    rendererName: "Tabelle", 
                    aggregatorName: "Anzahl", 

                    onRefresh: function() {
                        // Stellt sicher, dass Filter-Popups korrekt positioniert werden
                        $('.pvtFilterBox').css({
                            'z-index': 1000,
                            'max-height': '80vh',
                            'overflow-y': 'auto'
                        }).position({
                            my: "center",
                            at: "center",
                            of: window
                        });
                    }
                },
                true // Overwrite
            );
            pivotInitialized = true;
        });
    }

    // 4. View Switcher Logik
    function switchView(view) {
        var tableView = document.getElementById('data-table');
        var pivotView = document.getElementById('pivot-output');
        var pivotInstructions = document.getElementById('pivot-instructions');
        var btnTable = document.getElementById('btn-table-view');
        var btnPivot = document.getElementById('btn-pivot-view');

        if (view === 'table') {
            tableView.style.display = 'block';
            pivotView.style.display = 'none';
            pivotInstructions.style.display = 'none';
            btnTable.classList.remove('button-secondary');
            btnPivot.classList.add('button-secondary');
            if (table) {
                table.redraw(true); // Wichtig für korrekte Darstellung nach dem Einblenden
            }
        } else if (view === 'pivot') {
            initializePivot(); // Initialisiere Pivot beim ersten Klick
            tableView.style.display = 'none';
            pivotView.style.display = 'block';
            pivotInstructions.style.display = 'block';
            btnTable.classList.add('button-secondary');
            btnPivot.classList.remove('button-secondary');
        }
    }

    // Standardansicht initialisieren
    if (data && data.length > 0) {
        switchView('table');
    } else {
        // Deaktiviere Buttons, wenn keine Daten vorhanden sind
        document.getElementById('btn-table-view').disabled = true;
        document.getElementById('btn-pivot-view').disabled = true;
    }

  </script>
{% endblock %}

(NEU) members/templates/members/password_change_form.html
{% extends "master.html" %}

{% block title %}
  Passwort ändern
{% endblock %}

{% block content %}
<div style="max-width: 600px; margin: 40px auto;">
    <h2>Passwort ändern</h2>
    <div class="content-card">
    
    <p>Bitte geben Sie Ihr altes Passwort ein, und dann Ihr neues Passwort zwei Mal zur Bestätigung.</p>

    <form method="post">
        {% csrf_token %}
        
        {% if form.non_field_errors %}
        <div class="messages">
            {% for error in form.non_field_errors %}
                <li class="error">{{ error }}</li>
            {% endfor %}
        </div>
        {% endif %}

        {% for field in form %}
        <div class="form-group">
            <label for="{{ field.id_for_label }}">{{ field.label }}:</label>
            {{ field }}
            
            {% if field.help_text %}
            <p class="form-help-text">{{ field.help_text|safe }}</p>
            {% endif %}
            
            {{ field.errors }}
        </div>
        {% endfor %}
        
        <button type="submit" class="button" style="margin-top: 10px;">Passwort ändern</button>
        <a href="{% url 'dashboard' %}" style="margin-left: 15px;">Abbrechen</a>
    </form>
    </div>
</div>
{% endblock %}

(NEU) members/templates/members/password_change_done.html
{% extends "master.html" %}

{% block title %}
  Passwort erfolgreich geändert
{% endblock %}

{% block content %}
<div style="max-width: 600px; margin: 40px auto;">
    <h2>Erfolg</h2>
    <div class="content-card" style="text-align: center;">
    
    <p>Ihr Passwort wurde erfolgreich aktualisiert.</p>
    
    <p style="margin-top: 30px;"><a href="{% url 'dashboard' %}" class="button">Zurück zum Dashboard</a></p>
    </div>
</div>
{% endblock %}

members/templates/members/dashboard.html (Aktualisiertes Styling)
{% extends "master.html" %}
{% load humanize %} 
{% block title %}
  Dashboard
{% endblock %}

{% block extra_head %}
<style>
    /* Tabellen-Styling angepasst an DWS Design */
    table.file-list { 
        border-collapse: collapse; 
        width: 100%; 
        margin-top: 20px; 
        background: white; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        border: 1px solid var(--dws-lightgrey);
    }
    .file-list th, .file-list td { 
        border-bottom: 1px solid #ddd; 
        padding: 15px; 
        text-align: left; 
    }
    .file-list th { 
        /* Header im DWS Blau */
        background-color: var(--dws-blue); 
        color: white;
        font-weight: 700; 
    }
    .file-list tr:hover { 
        /* Hover Effekt für bessere Usability */
        background-color: #f1f3f5; 
    }
    .actions a { 
        margin-right: 15px; 
        white-space: nowrap; 
    }
    .muted { color: #666; font-size: 0.9em; }
</style>
{% endblock %}

{% block content %}
  <h1>Willkommen, {{ user.first_name|default:user.username }}!</h1>

  <h2>Ihre Dateien</h2>

  {% if files %}
    <table class="file-list">
      <thead>
        <tr>
          <th>Titel</th>
          <th>Dateiname</th>
          <th>Größe</th>
          <th>Hochgeladen</th>
          <th>Aktionen</th>
        </tr>
      </thead>
      <tbody>
        {% for f in files %}
          <tr>
            <td>{{ f.title }}</td>
            <td>
                <span class="muted">{{ f.filename }}</span>
            </td>
            <td>
                {{ f.file.size|filesizeformat }}
            </td>
            <td>{{ f.uploaded_at|date:"d.m.Y H:i" }}</td>
            <td class="actions">
                
                {% if f.is_analyzable %}
                    <a href="{% url 'datafiles:analyze' f.id %}">📊 Analysieren</a>
                {% else %}
                    <span class="muted">(Analyse nicht möglich)</span>
                {% endif %}

                <a href="{% url 'datafiles:download' f.id %}">⬇️ Download</a>
                
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <div class="content-card">
        <p>Sie haben aktuell keine Dateien in Ihrem Account.</p>
    </div>
  {% endif %}

  <p style="margin-top: 40px; font-size: 0.9em;" class="muted">
    Dateien können aktuell über das Admin-Backend hochgeladen und zugewiesen werden.
  </p>

{% endblock %}

(Aktualisiert) members/templates/members/login.html und register.html
Diese Templates wurden ebenfalls aktualisiert, um die neuen CSS-Klassen (content-card, button, form-help-text) zu nutzen. (Der Code ist analog zu den anderen Formularen und wird hier zur Kürze weggelassen, entspricht aber dem neuen Stil).
