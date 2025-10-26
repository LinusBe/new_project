from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Erweitert das Standard-Registrierungsformular um E-Mail, Vor- und Nachname.
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address") # KORREKTUR: eingerückt
    first_name = forms.CharField(required=True, label="First Name") # KORREKTUR: eingerückt
    last_name = forms.CharField(required=True, label="Last Name") # KORREKTUR: eingerückt

    # KORREKTUR: Klasse Meta eingerückt
    class Meta(UserCreationForm.Meta):
        model = User # KORREKTUR: eingerückt
        # Definiert die Felder, die im Formular angezeigt werden sollen.
        fields = ("username", "email", "first_name", "last_name") # KORREKTUR: eingerückt

    # KORREKTUR: Methode clean_email eingerückt
    def clean_email(self):
        # Stellt sicher, dass die E-Mail-Adresse einzigartig ist (case-insensitive).
        email = self.cleaned_data.get('email') # KORREKTUR: eingerückt
        if email and User.objects.filter(email__iexact=email).exists(): # KORREKTUR: eingerückt
            raise forms.ValidationError("A user with this email address already exists.") # KORREKTUR: eingerückt
        return email # KORREKTUR: eingerückt