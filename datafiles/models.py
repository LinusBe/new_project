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
        # Parquet ist jetzt "first class citizen"
        return self.get_file_extension() in ['.csv', '.xlsx', '.xls', '.pkl', '.xlsm', '.parquet'] # KORREKTUR: eingerückt

    # NEU: Methode zum Löschen der physischen Datei, wenn der DB-Eintrag gelöscht wird
    # KORREKTUR: delete eingerückt
    def delete(self, *args, **kwargs):
        # 1) Physische Original-Datei löschen
        self.file.delete(save=False) # KORREKTUR: eingerückt
        # 2) Cache entfernen (neu)
        try: # KORREKTUR: eingerückt
            from .cache import purge_cache_for
            purge_cache_for(self) # KORREKTUR: eingerückt
        except Exception: # KORREKTUR: eingerückt
            pass # KORREKTUR: eingerückt
        # 3) DB löschen
        super().delete(*args, **kwargs) # KORREKTUR: eingerückt
