from django.contrib import admin
from .models import DataFile

@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    # Angepasst von 'member' auf 'user'
    list_display = ("title", "user", "uploaded_at", "filename")
    list_filter = ("user__username",)
    # Suche nach Titel oder Benutzername/Name des Users
    search_fields = ("title", "user__username", "user__first_name", "user__last_name")
