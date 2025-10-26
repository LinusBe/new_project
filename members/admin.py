from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Member

# Definiert, wie das Member-Profil inline im User-Admin angezeigt wird.
class MemberInline(admin.StackedInline):
    model = Member # KORREKTUR: eingerückt
    can_delete = False # KORREKTUR: eingerückt
    verbose_name_plural = 'Member Profil Details (Telefon etc.)' # KORREKTUR: eingerückt
    fk_name = 'user' # KORREKTUR: eingerückt

# Definiert einen neuen User-Admin, der das Profil integriert.
class UserAdmin(BaseUserAdmin):
    inlines = (MemberInline,) # KORREKTUR: eingerückt
    # Zeigt das Beitrittsdatum (date_joined) in der Liste an
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined') # KORREKTUR: eingerückt

# Registrierung des neuen UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
