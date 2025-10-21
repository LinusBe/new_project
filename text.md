Absolut. Ich habe dein Django-Repository analysiert. Deine Grundstruktur war ein solider Ausgangspunkt, aber die Kernfunktionalitäten – sicheres Login, Zugriffsschutz und insbesondere die Online-Datenanalyse mit Filterung und Pivotierung – fehlten.
Ich habe das Projekt umfassend überarbeitet, um diese Anforderungen auf professionellem Niveau zu implementieren, unter Einhaltung von Django Best Practices.
Wichtigste Verbesserungen und Analyse
 * Authentifizierung & Benutzer:
   * Bisher: Das Member-Modell war ein einfaches Datenmodell ohne Login-Funktion.
   * Verbesserung: Ich habe das Standard-Django-User-Modell für die Authentifizierung integriert. Member wurde in ein Benutzerprofil (OneToOneField) umgewandelt. Login/Logout-Flows sind nun implementiert.
 * Sicherheit (Autorisierung):
   * Bisher: Views waren ungeschützt; jeder konnte potenziell Dateien anderer sehen.
   * Verbesserung: Alle relevanten Views sind nun mit @login_required geschützt. Es wird strikt geprüft, ob der eingeloggte Benutzer der Eigentümer der Datei ist.
 * Online-Analyse (Filterung und Pivotierung):
   * Bisher: Fehlte komplett.
   * Verbesserung: Das Kernstück der Überarbeitung. Eine neue View nutzt Pandas, um CSV- oder Excel-Dateien robust einzulesen (inklusive Handling für verschiedene Encodings und Separatoren). Die Daten werden als JSON an das Frontend übergeben. Dort kommt PivotTable.js zum Einsatz, eine leistungsstarke JavaScript-Bibliothek, die eine interaktive Drag-and-Drop-Pivot-Tabelle bereitstellt.
 * Dateiverwaltung:
   * Verbesserung: Dateien werden nun in benutzerspezifischen Ordnern (media/user_<id>/) gespeichert. Außerdem wird die physische Datei automatisch gelöscht, wenn der Datenbankeintrag entfernt wird.
Wichtige Hinweise zur Einrichtung
Achtung: Da sich die Datenbankstruktur grundlegend geändert hat (wir nutzen jetzt das User-Modell statt Member als Basis), musst du deine bestehende Datenbank und die alten Migrationen zurücksetzen.
 * Abhängigkeiten installieren:
   Für die Verarbeitung von Excel- und CSV-Dateien benötigen wir Pandas und OpenPyXL.
   pip install pandas openpyxl

 * Datenbank zurücksetzen (Löscht alle Daten!):
   Lösche deine db.sqlite3-Datei und alle .py-Dateien (außer __init__.py) in den Ordnern members/migrations/ und datafiles/migrations/.
 * Neue Migrationen erstellen und ausführen:
   python manage.py makemigrations members datafiles
python manage.py migrate
python manage.py createsuperuser

Du kannst nun über das Admin-Interface (/admin/) Benutzer anlegen und ihnen Dateien zuweisen (unter "Data files"). Diese Benutzer können sich dann im Frontend einloggen.
Das verbesserte Repository (Komplett)
Projektkonfiguration (solutiontrading)
C:\Users\dashboard\manage.py (Unverändert)
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'solutiontrading.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

C:\Users\dashboard\solutiontrading\settings.py (Aktualisiert)
"""
Django settings for solutiontrading project.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-=*ku3m@g&@&fe^@t)gofxe3m(d%y$7bo0yq#j)^_t#tvi(fsp4'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', # NEU: Für bessere Formatierung (z.B. Dateigrößen)
    'members.apps.MembersConfig',
    'datafiles.apps.DatafilesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'solutiontrading.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True, # Sucht Templates in den App-Verzeichnissen
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'solutiontrading.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# Geändert auf Deutsch und lokale Zeitzone
LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files (User Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# NEU: Authentication settings
LOGIN_REDIRECT_URL = 'dashboard' # Wohin nach dem Login
LOGOUT_REDIRECT_URL = 'login'    # Wohin nach dem Logout
LOGIN_URL = 'login'              # URL der Login-Seite

C:\Users\dashboard\solutiontrading\urls.py (Aktualisiert)
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Leitet die Root-URL ('/') zum Dashboard weiter.
    # Wenn der User nicht eingeloggt ist, leitet das Dashboard ihn zum Login weiter.
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),

    # URLs für Account-Management (Login, Logout, Dashboard)
    path('account/', include('members.urls')),

    # URLs für Dateiverwaltung (Download, View) unter dem Präfix /files/
    path('files/', include('datafiles.urls', namespace='datafiles')),

    path('admin/', admin.site.urls),
]

# Servieren von Media-Dateien (User Uploads) im Entwicklungsmodus
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

( asgi.py, wsgi.py und __init__.py bleiben unverändert wie im Original und werden hier zur Kürze weggelassen.)
App: members (Authentifizierung & Profile)
C:\Users\dashboard\members\models.py (Überarbeitet)
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Wir verwenden das Member-Modell als Profilerweiterung (Profile) für den Standard-User.
class Member(models.Model):
  # related_name="profile" erlaubt den Zugriff via user.profile
  user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
  # Felder wie firstname, lastname, joined_date werden vom User-Modell übernommen.
  # CharField ist besser für Telefonnummern als IntegerField.
  phone = models.CharField(max_length=50, null=True, blank=True)

  def __str__(self):
    # Zeigt den vollen Namen an, falls verfügbar, sonst den Benutzernamen
    return self.user.get_full_name() or self.user.username

# Signal, um automatisch ein Member-Profil zu erstellen/aktualisieren, wenn ein User gespeichert wird.
@receiver(post_save, sender=User)
def create_or_update_user_member(sender, instance, created, **kwargs):
    # Stellt sicher, dass ein Profil existiert und gespeichert wird.
    # get_or_create ist robust für bestehende User und neue User.
    member, created_profile = Member.objects.get_or_create(user=instance)
    if not created:
        member.save()

C:\Users\dashboard\members\admin.py (Überarbeitet)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Member

# Definiert, wie das Member-Profil inline im User-Admin angezeigt wird.
class MemberInline(admin.StackedInline):
    model = Member
    can_delete = False
    verbose_name_plural = 'Member Profil Details (Telefon etc.)'
    fk_name = 'user'

# Definiert einen neuen User-Admin, der das Profil integriert.
class UserAdmin(BaseUserAdmin):
    inlines = (MemberInline,)
    # Zeigt das Beitrittsdatum (date_joined) in der Liste an
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')

# Registrierung des neuen UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

C:\Users\dashboard\members\views.py (Überarbeitet)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Das Dashboard ist der zentrale Ort für den Benutzer.
@login_required
def dashboard(request):
  # Dateien des eingeloggten Benutzers abrufen.
  # Wir nutzen den related_name 'datafiles' aus dem DataFile Modell.
  files = request.user.datafiles.all().order_by('-uploaded_at')

  context = {
    'user': request.user,
    'files': files
  }
  return render(request, 'members/dashboard.html', context)

# Die ursprünglichen Views main, members, details, testing wurden entfernt oder ersetzt.

C:\Users\dashboard\members\urls.py (Überarbeitet)
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

# URLs sind unter /account/ erreichbar (siehe solutiontrading/urls.py)

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),

    # Nutzt Djangos eingebaute Auth Views für Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='members/login.html'), name='login'),
    # Logout wird durch settings.LOGOUT_REDIRECT_URL gesteuert
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

C:\Users\dashboard\members\apps.py (Unverändert)
from django.apps import AppConfig


class MembersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'members'

App: datafiles (Dateiverwaltung & Analyse)
C:\Users\dashboard\datafiles\models.py (Überarbeitet)
from django.db import models
from django.conf import settings
import os

# Funktion zur Definition des Upload-Pfads (benutzerspezifische Ordner)
def user_directory_path(instance, filename):
    # Datei wird hochgeladen nach MEDIA_ROOT/user_<id>/<filename>
    return f'user_{instance.user.id}/{filename}'

class DataFile(models.Model):
    # Verknüpfung direkt zum Standard User-Modell (settings.AUTH_USER_MODEL)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='datafiles' # Wichtig für den Zugriff: user.datafiles.all()
    )
    title = models.CharField(max_length=255)
    
    # Nutzt die neue Pfadfunktion.
    file = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    # Hilfsmethode für den Dateinamen
    def filename(self):
        return os.path.basename(self.file.name)

    # Hilfsmethode zur Prüfung des Dateityps
    def get_file_extension(self):
        name, extension = os.path.splitext(self.file.name)
        return extension.lower()

    def is_analyzable(self):
        # Prüft, ob der Dateityp online analysiert werden kann
        return self.get_file_extension() in ['.csv', '.xlsx', '.xls']

    # NEU: Methode zum Löschen der physischen Datei, wenn der DB-Eintrag gelöscht wird
    def delete(self, *args, **kwargs):
        # Löscht die Datei aus dem Media-Speicher
        self.file.delete(save=False)
        super().delete(*args, **kwargs)

C:\Users\dashboard\datafiles\admin.py (Überarbeitet)
from django.contrib import admin
from .models import DataFile

@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    # Angepasst von 'member' auf 'user'
    list_display = ("title", "user", "uploaded_at", "filename")
    list_filter = ("user__username",)
    # Suche nach Titel oder Benutzername/Name des Users
    search_fields = ("title", "user__username", "user__first_name", "user__last_name")

C:\Users\dashboard\datafiles\views.py (Überarbeitet und Erweitert)
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import DataFile
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.contrib import messages
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

@login_required
def download_file(request, file_id):
    # SICHERHEIT: Sicherstellen, dass die Datei existiert UND dem aktuellen Benutzer gehört.
    try:
        # Wir verwenden user=request.user direkt im Query.
        f = DataFile.objects.get(pk=file_id, user=request.user)
    except DataFile.DoesNotExist:
        # Unterscheidung zwischen Forbidden und NotFound
        if DataFile.objects.filter(pk=file_id).exists():
            return HttpResponseForbidden("Sie haben keine Berechtigung zum Zugriff auf diese Datei.")
        raise Http404("Datei nicht gefunden.")

    if not f.file:
        raise Http404("Datei nicht im Speicher vorhanden.")

    # FileResponse ist effizient für das Streaming von Dateien.
    return FileResponse(f.file.open('rb'), as_attachment=True, filename=f.filename())

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
         messages.error(request, f"Dieser Dateityp ({data_file.get_file_extension()}) kann nicht online analysiert werden (nur CSV/Excel).")
         return redirect('dashboard')

    # Datei mit Pandas lesen
    try:
        # Wir lesen die Datei in den Speicher, um robustes Format-Sniffing zu ermöglichen.
        # Dies ist für moderate Dateigrößen akzeptabel.
        file_content = data_file.file.read()
        extension = data_file.get_file_extension()

        if extension == '.csv':
            # Robustes CSV Handling
            df = read_csv_robust(file_content)
            
        elif extension in ['.xlsx', '.xls']:
            df = pd.read_excel(io.BytesIO(file_content))

        # NaN/Null-Werte behandeln (Ersetzen durch leeren String für die Anzeige)
        df = df.fillna('')

        # DataFrame in JSON konvertieren (Format: Liste von Objekten)
        # Dies ist das bevorzugte Format für PivotTable.js
        data_json = df.to_json(orient='records', date_format='iso', default_handler=str)

    except Exception as e:
        logger.error(f"Fehler beim Analysieren der Datei {file_id}: {e}")
        messages.error(request, f"Fehler beim Lesen oder Verarbeiten der Datei: {e}")
        return redirect('dashboard')

    return render(request, 'datafiles/analyze.html', {
        'data_file': data_file,
        'data_json': data_json
    })

def read_csv_robust(file_content_bytes):
    """Hilfsfunktion zum Lesen von CSVs mit verschiedenen Encodings und Separatoren."""
    # Gängige Encodings (UTF-8, Westeuropäisch/Deutsch)
    encodings = ['utf-8', 'latin1', 'windows-1252']
    separators = [',', ';']

    for encoding in encodings:
        for separator in separators:
            try:
                # Dekodieren der Bytes zu String
                decoded_content = file_content_bytes.decode(encoding)
                # Lesen des Strings mit Pandas
                df = pd.read_csv(io.StringIO(decoded_content), sep=separator)
                
                # Prüfen, ob das Ergebnis sinnvoll ist:
                # Wenn mehr als 1 Spalte gelesen wurde, war der Separator wahrscheinlich richtig.
                if len(df.columns) > 1:
                    return df
                # Wenn nur 1 Spalte gelesen wurde, aber die Datei nicht leer ist, akzeptieren wir es auch (könnte eine einspaltige Datei sein).
                if len(df.columns) == 1 and not df.empty:
                     return df

            except UnicodeDecodeError:
                continue # Nächstes Encoding versuchen
            except Exception as e:
                logger.warning(f"Fehler beim Versuch mit {encoding}/{separator}: {e}")
                continue # Nächstes Format versuchen
    
    # Wenn keine Kombination funktioniert hat
    raise ValueError("Konnte das CSV-Format (Encoding/Separator) nicht bestimmen.")

C:\Users\dashboard\datafiles\urls.py (Überarbeitet)
from django.urls import path
from . import views

# Define an app_name for namespacing (z.B. {% url 'datafiles:download' %})
app_name = 'datafiles'

# URLs sind unter /files/ erreichbar (siehe solutiontrading/urls.py)
urlpatterns = [
    path('<int:file_id>/download/', views.download_file, name='download'),
    path('<int:file_id>/analyze/', views.analyze_file, name='analyze'),
]

C:\Users\dashboard\datafiles\apps.py (Unverändert)
from django.apps import AppConfig


class DatafilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'datafiles'

Templates
Die Templates wurden neu strukturiert, um ein konsistentes Layout und die neuen Funktionen zu unterstützen. Wir legen sie in den jeweiligen App-Ordnern ab.
(NEU/Überarbeitet) C:\Users\dashboard\members\templates\master.html (Basis-Template)
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Datenportal{% endblock %}</title>
  <style>
    /* Globales CSS Styling */
    body { font-family: system-ui, Arial, sans-serif; margin: 0; background-color: #f4f4f9; color: #333; }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    nav { background: #ffffff; padding: 15px 20px; color: #333; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
    nav a { text-decoration: none; color: #0056b3; padding: 5px 10px; }
    nav a:hover { background: #eef; }
    .logo { font-weight: bold; font-size: 1.2em; }
    
    /* Styling für Django Messages (Flash-Nachrichten) */
    .messages { list-style-type: none; padding: 0; margin-bottom: 20px; }
    .messages li { padding: 10px 15px; border-radius: 5px; border: 1px solid transparent; margin-bottom: 10px; }
    .messages .info { background-color: #d9edf7; color: #31708f; border-color: #bce8f1; }
    .messages .success { background-color: #dff0d8; color: #3c763d; border-color: #d6e9c6; }
    .messages .warning { background-color: #fcf8e3; color: #8a6d3b; border-color: #faebcc; }
    .messages .error { background-color: #f2dede; color: #a94442; border-color: #ebccd1; }
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
            {% if user.is_staff %}
            <a href="{% url 'admin:index' %}">Admin</a> |
            {% endif %}
            <a href="{% url 'logout' %}">Logout</a>
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

(NEU) C:\Users\dashboard\members\templates\members\login.html
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
    <div style="margin-bottom: 15px;">
        <label for="{{ form.username.id_for_label }}">Benutzername:</label><br>
        {{ form.username }}
        {{ form.username.errors }}
    </div>
    <div style="margin-bottom: 20px;">
        <label for="{{ form.password.id_for_label }}">Passwort:</label><br>
        {{ form.password }}
        {{ form.password.errors }}
    </div>
    
    <button type="submit" style="width: 100%; padding: 10px; background-color: #0056b3; color: white; border: none; border-radius: 5px; cursor: pointer;">Login</button>
    
    <input type="hidden" name="next" value="{{ next }}">
  </form>
</div>
{% endblock %}

(NEU) C:\Users\dashboard\members\templates\members\dashboard.html
{% extends "master.html" %}
{% load humanize %} {% block title %}
  Dashboard
{% endblock %}

{% block extra_head %}
<style>
    /* Tabellen-Styling */
    table.file-list { border-collapse: collapse; width: 100%; margin-top: 20px; background: white; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
    .file-list th, .file-list td { border: 1px solid #ddd; padding: 12px 15px; text-align: left; }
    .file-list th { background-color: #f5f5f5; font-weight: bold; }
    .file-list tr:nth-child(even) { background-color: #fafafa; }
    .actions a { margin-right: 15px; text-decoration: none; color: #007bff; white-space: nowrap; }
    .actions a:hover { text-decoration: underline; }
    .muted { color: #666; font-size: 0.9em; }
</style>
{% endblock %}

{% block content %}
  <h1>Hallo, {{ user.first_name|default:user.username }}!</h1>

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
    <p>Sie haben aktuell keine Dateien in Ihrem Account.</p>
  {% endif %}

  <p style="margin-top: 40px; font-size: 0.9em;" class="muted">
    Dateien können aktuell über das Admin-Backend hochgeladen und zugewiesen werden.
  </p>

{% endblock %}

(NEU) C:\Users\dashboard\datafiles\templates\datafiles\analyze.html
{% extends "master.html" %}

{% block title %}
  Analyse: {{ data_file.title }}
{% endblock %}

{% block extra_head %}
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js"></script>
    
    <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/pivot.min.js"></script>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.17/d3.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.js"></script>
    <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/c3/0.4.11/c3.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pivottable/2.23.0/c3_renderers.min.js"></script>


    <style>
        /* Styling für die Pivot-Tabelle */
        #output { margin-top: 20px; background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        .pvtUi { width: 100%; font-size: 13px; }
        /* Anpassung des Containers, da Pivot-Tabellen oft breit sind */
        #main-container { max-width: 98%; } 
    </style>
{% endblock %}

{% block content %}
  <h1>Datenanalyse: {{ data_file.title }}</h1>
  <p>
    <a href="{% url 'dashboard' %}">&larr; Zurück zum Dashboard</a> | 
    <a href="{% url 'datafiles:download' data_file.id %}">Originaldatei herunterladen</a>
  </p>

  <div id="output">Lade interaktive Pivot-Tabelle...</div>

  <script type="text/javascript">
    $(function(){
        // Laden der Daten, die von der Django View übergeben wurden
        // Wichtig: |safe Filter verwenden, damit Django den JSON-String direkt als JavaScript-Objekt einbettet.
        var data = {{ data_json|safe }};

        // Standard-Renderer mit C3-Diagramm-Renderern kombinieren
        var renderers = $.extend(
            $.pivotUtilities.renderers,
            $.pivotUtilities.c3_renderers
        );

        // Initialisierung der PivotTable UI
        $("#output").pivotUI(
            data,
            {
                renderers: renderers,
                // Optional: Hier können Sie Zeilen/Spalten vorkonfigurieren
                // rows: ["Kategorie"],
                // cols: ["Jahr"],
                rendererName: "Table" // Standard-Renderer beim Laden
            },
            true // Overwrite den Containerinhalt
        );
    });
  </script>
{% endblock %}

