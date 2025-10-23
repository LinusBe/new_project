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
