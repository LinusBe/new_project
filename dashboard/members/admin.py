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
