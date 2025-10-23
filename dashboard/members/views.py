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
        # Zeigt das
 leere Formular an (GET-Anfrage)
        form = CustomUserCreationForm()

    return render(request, 'members/register.html', {'form': form})
