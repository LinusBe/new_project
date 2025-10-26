from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm

# Das Dashboard ist der zentrale Ort für den Benutzer.
@login_required
def dashboard(request):
    # Dateien des eingeloggten Benutzers abrufen.
    files = request.user.datafiles.all().order_by('-uploaded_at') # KORREKTUR: eingerückt

    context = { # KORREKTUR: eingerückt
        'user': request.user,
        'files': files
    }
    return render(request, 'members/dashboard.html', context) # KORREKTUR: eingerückt

# NEU: View für die Benutzererstellung durch eingeloggte Benutzer
@login_required
def register_user(request):
    if request.method == 'POST': # KORREKTUR: eingerückt
        form = CustomUserCreationForm(request.POST) # KORREKTUR: eingerückt
        if form.is_valid(): # KORREKTUR: eingerückt
            # Speichert den neuen Benutzer
            user = form.save() # KORREKTUR: eingerückt
            # Hinweis: Der Benutzer wird nicht automatisch eingeloggt, da dies den aktuellen User ausloggen würde.
            messages.success(request, f"User {user.username} created successfully. The password was set in the form.") # KORREKTUR: eingerückt
            # Weiterleitung zum Dashboard
            return redirect('dashboard') # KORREKTUR: eingerückt
        else: # KORREKTUR: eingerückt
            # Zeigt Fehler im Formular an
            messages.error(request, "Error creating user. Please check the inputs.") # KORREKTUR: eingerückt
   
    else: # KORREKTUR: eingerückt
        # Zeigt das leere Formular an (GET-Anfrage)
        form = CustomUserCreationForm() # KORREKTUR: eingerückt

    return render(request, 'members/register.html', {'form': form}) # KORREKTUR: eingerückt
