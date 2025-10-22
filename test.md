Das ist ein sehr gutes Update. Ich habe deine Anforderungen analysiert, die bestehenden Probleme behoben und die gewünschten Erweiterungen implementiert, aufbauend auf der Struktur der letzten Antwort.
Hier ist die detaillierte Analyse und das darauf aufbauende, vollständige Repository.
Wichtiger Hinweis zur Einrichtung
Für die verbesserte, robuste Erkennung von CSV-Dateiformaten (Encoding und Separatoren) nutzen wir nun die Bibliothek chardet. Bitte installiere diese zusätzlich zu Pandas und OpenPyXL:
pip install pandas openpyxl chardet

Detaillierte Analyse und Verbesserungen
1. Bereinigung des alten Repositories
Die folgenden Dateien aus deinem ursprünglichen Projekt sind obsolet und können gelöscht werden, da ihre Funktionen ersetzt wurden:
 * C:\Users\dashboard\members\templates\all_members.html
 * C:\Users\dashboard\members\templates\details.html
 * C:\Users\dashboard\members\templates\main.html
 * C:\Users\dashboard\members\templates\myfirst.html
 * C:\Users\dashboard\members\templates\template.html
 * C:\Users\dashboard\datafiles\templates\index.html
 * C:\Users\dashboard\datafiles\templates\datafiles\member_files.html
2. Problembehebung: Dateizugriff und Analyse
Du hast berichtet, dass der Zugriff auf die Dateien nicht funktioniert. Ich habe die Verarbeitung signifikant robuster gestaltet:
 * Automatisierte Erkennung: Nutzung von chardet zur automatischen Erkennung des Encodings (z.B. UTF-8, Latin1) und zuverlässige Ermittlung des Separators (Komma, Semikolon).
 * Robuste Datenkonvertierung: Ich habe eine dedizierte Funktion (prepare_dataframe_for_json) hinzugefügt. Diese stellt sicher, dass alle Datentypen (Datum, Zahlen, Nullwerte, Infinities) korrekt bereinigt und in ein Format konvertiert werden, das von der JavaScript-Analyse fehlerfrei verarbeitet wird, ohne dabei Typinformationen (z.B. Zahl vs. Text) zu verlieren.
3. Vereinfachte Rollen und Benutzererstellung
 * Rollen (Admin vs. User): Das System nutzt die einfache Unterscheidung von Django (User vs. Staff/Admin). Das passt.
 * Benutzererstellung durch User: Gemäß deiner Anforderung habe ich eine Funktion implementiert, die es eingeloggten Benutzern erlaubt, neue Benutzerkonten anzulegen.
4. Evaluation: Streamlit und DuckDB
Wir behalten den aktuellen Stack (Django, Pandas, PivotTable.js) bei. Dieser bietet die beste Balance aus Integration (Authentifizierung), Flexibilität und Leistung für moderate Dateigrößen.
5. Funktionalität: Online-Analyse (Pivot, Filter, Auswertung)
Um die Funktionalität sicherzustellen, habe ich analyze.html optimiert:
 * Abhängigkeiten: Sicherstellung, dass jQuery UI (für Drag&Drop) und C3.js (für Diagramme) korrekt geladen werden.
 * Lokalisierung: PivotTable.js wurde auf Deutsch konfiguriert.
Das vollständige, verbesserte Repository
Hier ist der gesamte Code des Projekts.
Projektkonfiguration (solutiontrading)
(manage.py, asgi.py, wsgi.py unverändert wie im Original.)
(settings.py, urls.py unverändert zur letzten Version. Siehe vorherige Antwort für den Code.)
App: members (Authentifizierung, Profile, Registrierung)
(models.py, admin.py, apps.py unverändert zur letzten Version.)
(NEU) C:\Users\dashboard\members\forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Erweitert das Standard-Registrierungsformular um E-Mail, Vor- und Nachname.
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="E-Mail-Adresse")
    first_name = forms.CharField(required=True, label="Vorname")
    last_name = forms.CharField(required=True, label="Nachname")

    class Meta(UserCreationForm.Meta):
        model = User
        # Definiert die Felder, die im Formular angezeigt werden sollen.
        fields = ("username", "email", "first_name", "last_name")

    def clean_email(self):
        # Stellt sicher, dass die E-Mail-Adresse einzigartig ist (case-insensitive).
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ein Benutzer mit dieser E-Mail-Adresse existiert bereits.")
        return email

C:\Users\dashboard\members\views.py (Aktualisiert)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm

# Das Dashboard ist der zentrale Ort für den Benutzer.
@login_required
def dashboard(request):
  # Dateien des eingeloggten Benutzers abrufen.
  files = request.user.datafiles.all().order_by('-uploaded_at')

  context = {
    'user': request.user,
    'files': files
  }
  return render(request, 'members/dashboard.html', context)

# NEU: View für die Benutzererstellung durch eingeloggte Benutzer
@login_required
def register_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Speichert den neuen Benutzer
            user = form.save()
            # Hinweis: Der Benutzer wird nicht automatisch eingeloggt, da dies den aktuellen User ausloggen würde.
            messages.success(request, f"Benutzer {user.username} erfolgreich angelegt. Das Passwort wurde im Formular festgelegt.")
            # Weiterleitung zum Dashboard
            return redirect('dashboard')
        else:
            # Zeigt Fehler im Formular an
            messages.error(request, "Fehler beim Anlegen des Benutzers. Bitte überprüfen Sie die Eingaben.")
    else:
        # Zeigt das leere Formular an (GET-Anfrage)
        form = CustomUserCreationForm()
    
    return render(request, 'members/register.html', {'form': form})

C:\Users\dashboard\members\urls.py (Aktualisiert)
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

# URLs sind unter /account/ erreichbar (siehe solutiontrading/urls.py)

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),

    # NEU: Registrierung (nur für eingeloggte User)
    path('register/', views.register_user, name='register_user'),

    # Nutzt Djangos eingebaute Auth Views für Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='members/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

App: datafiles (Dateiverwaltung & Analyse)
(models.py, admin.py, urls.py, apps.py unverändert zur letzten Version.)
C:\Users\dashboard\datafiles\views.py (Stark verbessert)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DataFile
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.contrib import messages
import pandas as pd
import io
import logging
import chardet # NEU: Für verbesserte Encoding-Erkennung
import numpy as np

logger = logging.getLogger(__name__)

@login_required
def download_file(request, file_id):
    # SICHERHEIT: Sicherstellen, dass die Datei existiert UND dem aktuellen Benutzer gehört.
    try:
        f = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        # Unterscheidung zwischen Forbidden und NotFound
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
         messages.warning(request, f"Dieser Dateityp ({data_file.get_file_extension()}) kann nicht online analysiert werden (nur CSV/Excel).")
         return redirect('dashboard')

    if not data_file.file.storage.exists(data_file.file.name):
        raise Http404("Datei nicht im Speicher vorhanden.")

    # Datei mit Pandas lesen
    try:
        file_content = data_file.file.read()
        extension = data_file.get_file_extension()

        if extension == '.csv':
            # Robustes CSV Handling
            df = read_csv_robust(file_content)
            
        elif extension in ['.xlsx', '.xls']:
            # Excel-Dateien werden direkt aus Bytes gelesen
            df = pd.read_excel(io.BytesIO(file_content))

        # Datenbereinigung und Konvertierung für JSON-Kompatibilität
        df = prepare_dataframe_for_json(df)

        # DataFrame in JSON konvertieren (Format: Liste von Objekten)
        # default_handler=str ist ein letzter Fallback für Typen, die wir nicht abgedeckt haben.
        data_json = df.to_json(orient='records', date_format='iso', default_handler=str)

    except ValueError as e:
        # Spezifischer Fehler von read_csv_robust
        logger.error(f"Fehler beim Bestimmen des CSV-Formats für Datei {file_id}: {e}")
        messages.error(request, f"Fehler beim Lesen der CSV-Datei: {e}")
        return redirect('dashboard')
    except Exception as e:
        # Allgemeiner Fehler beim Parsen oder Konvertieren
        logger.error(f"Unerwarteter Fehler beim Analysieren der Datei {file_id}: {e}", exc_info=True)
        messages.error(request, f"Ein unerwarteter Fehler ist aufgetreten beim Verarbeiten der Datei: {type(e).__name__}")
        return redirect('dashboard')

    return render(request, 'datafiles/analyze.html', {
        'data_file': data_file,
        'data_json': data_json
    })

def prepare_dataframe_for_json(df):
    """Bereinigt DataFrame-Typen für eine sichere JSON-Serialisierung, ohne Datentypen zu verlieren."""
    
    # NaN/Null-Werte behandeln (Ersetzen durch None, was in JSON zu null wird)
    # Dies ist wichtig, damit PivotTable.js fehlende Werte korrekt behandelt.
    df = df.replace({np.nan: None})

    # Konvertieren von Spaltentypen
    for col in df.columns:
        # Behandeln von Datetime-Objekten
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            # Konvertieren zu formatierten Strings, NaT (Not a Time) wird zu None
            df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').replace('NaT', None)
        
        # Behandeln von numerischen Typen (z.B. numpy.int64)
        elif pd.api.types.is_numeric_dtype(df[col]):
            # Sicherstellen, dass keine Infinitäten vorhanden sind (JSON-Standard unterstützt Inf nicht)
            df[col] = df[col].replace([np.inf, -np.inf], None)
            
            # Konvertieren zu Standard-Python-Typen (int oder float), um Numpy-Typen zu vermeiden
            # Diese Konvertierung stellt sicher, dass die JSON-Serialisierung funktioniert.
            # Wir prüfen, ob ein Float eine Ganzzahl ist, um den Typ korrekt zu erhalten.
            df[col] = df[col].apply(lambda x: x if x is None else (int(x) if isinstance(x, float) and x.is_integer() else float(x)))

        # Behandeln von Objekten (oft Strings)
        elif pd.api.types.is_object_dtype(df[col]):
             # Sicherstellen, dass alles andere ein String ist, außer None
             df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
             
    return df


def read_csv_robust(file_content_bytes):
    """Hilfsfunktion zum Lesen von CSVs mit automatischem Encoding und Separator Sniffing."""
    
    # 1. Encoding bestimmen mit chardet (analysiert die ersten 100KB)
    detection = chardet.detect(file_content_bytes[:102400]) 
    encoding = detection.get('encoding')
    
    if not encoding:
        encoding = 'utf-8' # Fallback

    # Gängige Separatoren
    separators = [',', ';', '\t', '|']
    
    best_df = None
    max_cols = 0

    # Liste der zu versuchenden Encodings (Erkanntes zuerst, dann Fallbacks)
    encodings_to_try = [encoding]
    if encoding.lower() != 'utf-8': encodings_to_try.append('utf-8')
    if encoding.lower() != 'latin1': encodings_to_try.append('latin1') # Häufig in DE/Windows

    for enc in encodings_to_try:
        try:
            # Zuerst versuchen wir zu dekodieren
            decoded_content = file_content_bytes.decode(enc)
        except UnicodeDecodeError:
            continue # Nächstes Encoding versuchen

        for separator in separators:
            try:
                # engine='python' ist robuster bei komplexen Formaten als die Standard-C-Engine
                df = pd.read_csv(io.StringIO(decoded_content), sep=separator, engine='python')
                
                num_cols = len(df.columns)

                # Heuristik: Der Separator, der die meisten Spalten liefert, ist wahrscheinlich der richtige.
                if num_cols > max_cols:
                    max_cols = num_cols
                    best_df = df
                
                # Wenn wir mehr als eine Spalte haben, sind wir oft erfolgreich.
                if num_cols > 1:
                    return df

            except Exception:
                # Fehler ignorieren (z.B. ParserError) und nächste Kombination versuchen
                continue

    if best_df is not None:
        return best_df

    # Wenn keine Kombination funktioniert hat
    raise ValueError("Konnte das CSV-Format (Encoding/Separator) nicht zuverlässig bestimmen.")

Templates
C:\Users\dashboard\members\templates\master.html (Aktualisiert)
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Datenportal{% endblock %}</title>
  <style>
    /* Globales CSS Styling */
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 0; background-color: #f4f4f9; color: #333; line-height: 1.6; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    nav { background: #ffffff; padding: 10px 20px; color: #333; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
    nav a { text-decoration: none; color: #0056b3; padding: 5px 10px; border-radius: 4px; }
    nav a:hover { background: #eef; }
    .logo { font-weight: bold; font-size: 1.2em; }
    .user-info { font-size: 0.9em; }
    
    /* Styling für Django Messages (Flash-Nachrichten) */
    .messages { list-style-type: none; padding: 0; margin-bottom: 20px; }
    .messages li { padding: 10px 15px; border-radius: 5px; border: 1px solid transparent; margin-bottom: 10px; }
    .messages .info { background-color: #d9edf7; color: #31708f; border-color: #bce8f1; }
    .messages .success { background-color: #dff0d8; color: #3c763d; border-color: #d6e9c6; }
    .messages .warning { background-color: #fcf8e3; color: #8a6d3b; border-color: #faebcc; }
    .messages .error { background-color: #f2dede; color: #a94442; border-color: #ebccd1; }

    /* Formular Styling (Global) */
    .form-group { margin-bottom: 15px; }
    label { display: block; margin-bottom: 5px; font-weight: 500; }
    input[type=text], input[type=password], input[type=email] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
    .errorlist { color: #a94442; list-style-type: none; padding-left: 0; font-size: 0.85em; margin-top: 5px;}
    button { padding: 10px 15px; background-color: #0056b3; color: white; border: none; border-radius: 5px; cursor: pointer; }
    button:hover { background-color: #004494; }

  </style>
  {% block extra_head %}{% endblock %}
</head>
<body>

<nav>
    <div class="logo">
        <a href="{% url 'dashboard' %}">Datenportal</a>
    </div>
    <div class="user-info">
        {% if user.is_authenticated %}
            Angemeldet als <strong>{{ user.get_full_name|default:user.username }}</strong> |
            
            <a href="{% url 'register_user' %}">Neuen User anlegen</a> |

            {% if user.is_staff %}
            <a href="{% url 'admin:index' %}">Admin</a> |
            {% endif %}
            <a href="{% url 'logout' %}">Logout</a>
        {% else %}
            <a href="{% url 'login' %}">Login</a>
            {# Öffentliche Registrierung ist nicht aktiv #}
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

C:\Users\dashboard\members\templates\members\login.html (Unverändert zur letzten Version, übernimmt neues Styling)
{% extends "master.html" %}

{% block title %}
  Login
{% endblock %}

{% block content %}
<div style="max-width: 400px; margin: 50px auto; padding: 30px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
  <h2>Login</h2>
  
  {# Zeigt allgemeine Formularfehler (z.B. falsche Kombination) #}
  {% if form.non_field_errors %}
    <div class="messages">
        <li class="error">Benutzername oder Passwort ist falsch. Bitte versuchen Sie es erneut.</li>
    </div>
  {% endif %}

  <form method="post">
    {% csrf_token %}
    
    <div class="form-group">
        <label for="{{ form.username.id_for_label }}">Benutzername:</label>
        {{ form.username }}
        {{ form.username.errors }}
    </div>
    <div class="form-group">
        <label for="{{ form.password.id_for_label }}">Passwort:</label>
        {{ form.password }}
        {{ form.password.errors }}
    </div>
    
    <button type="submit" style="width: 100%;">Login</button>
    
    <input type="hidden" name="next" value="{{ next }}">
  </form>

  <p style="margin-top: 20px; text-align: center; color: #666;">
    Zugang muss durch einen bestehenden Benutzer erstellt werden.
  </p>
</div>
{% endblock %}

(NEU) C:\Users\dashboard\members\templates\members\register.html
{% extends "master.html" %}

{% block title %}
  Neuen Benutzer anlegen
{% endblock %}

{% block content %}
<div style="max-width: 600px; margin: 40px auto; padding: 30px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
  <h2>Neuen Account erstellen</h2>
  
  <p><a href="{% url 'dashboard' %}">&larr; Zurück zum Dashboard</a></p>

  <form method="post">
    {% csrf_token %}
    
    {# Iteriert durch alle Felder des Formulars #}
    {% for field in form %}
      <div class="form-group">
        <label for="{{ field.id_for_label }}">{{ field.label }}:</label>
        {{ field }}
        
        {# Zeigt Hilfetexte an (z.B. Passwortanforderungen) #}
        {% if field.help_text %}
          <p style="font-size: 0.8em; color: #666; margin-top: 5px;">{{ field.help_text|safe }}</p>
        {% endif %}
        
        {# Zeigt Fehler für dieses spezifische Feld an #}
        {{ field.errors }}
      </div>
    {% endfor %}
    
    <button type="submit" style="margin-top: 10px;">Benutzer anlegen</button>
  </form>

</div>
{% endblock %}

(dashboard.html unverändert zur letzten Version.)
C:\Users\dashboard\datafiles\templates\datafiles\analyze.html (Optimiert und Lokalisiert)
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


    <style>
        /* Styling für die Pivot-Tabelle */
        #output { margin-top: 20px; background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        .pvtUi { width: 100%; font-size: 13px; }
        /* Anpassung des Containers, da Pivot-Tabellen oft breit sind */
        #main-container { max-width: 98%; } 

        /* Verhindert, dass der Body scrollt, wenn das Filter-Popup offen ist */
        body.pvtBody { overflow: hidden; } 

        .instructions { background: #e9f5ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #bce8f1; }
    </style>
{% endblock %}

{% block content %}
  <h1>Datenanalyse: {{ data_file.title }}</h1>
  <p>
    <a href="{% url 'dashboard' %}">&larr; Zurück zum Dashboard</a> | 
    <a href="{% url 'datafiles:download' data_file.id %}">Originaldatei herunterladen</a>
  </p>
  
  <div class="instructions">
    <strong>Anleitung:</strong> Ziehen Sie die Felder (Attribute) per Drag & Drop, um die Tabelle zu pivotieren. Nutzen Sie die Dropdown-Menüs, um Aggregationen (z.B. Summe) oder Visualisierungen (z.B. Balkendiagramm) auszuwählen. Klicken Sie auf die Pfeile neben den Attributen, um Filter anzuwenden.
  </div>

  <div id="output">Lade interaktive Pivot-Tabelle...</div>

  <script type="text/javascript">
    $(function(){
        // 1. Daten laden (von Django View übergeben)
        // |safe Filter ist notwendig, damit der JSON-String korrekt eingebettet wird.
        var data = {{ data_json|safe }};

        // 2. Lokalisierung laden (Deutsch)
        var localization = $.pivotUtilities.locales.de;

        // 3. Renderer konfigurieren (Deutsche Standard-Renderer + C3 Charts)
        // Wir nutzen $.extend, um die Renderer zu kombinieren.
        var renderers = $.extend(
            {},
            localization.renderers,
            $.pivotUtilities.c3_renderers
        );

        // 4. PivotTable UI initialisieren
        $("#output").pivotUI(
            data,
            {
                renderers: renderers,
                // Lokalisierung anwenden
                localeStrings: localization.localeStrings,
                rendererName: "Tabelle", // Standardansicht
                aggregatorName: "Anzahl", // Standardaggregation

                // Stellt sicher, dass die Filter-Popups korrekt positioniert werden (jQuery UI .position())
                onRefresh: function() {
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
            true // Overwrite den Containerinhalt
        );
    });
  </script>
{% endblock %}

