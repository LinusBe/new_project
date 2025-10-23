from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
# URLs sind unter /account/ erreichbar (siehe solutiontrading/urls.py)

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register_user, name='register_user'),
    # Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='members/login.html'), name='login'),
    # Logout wird durch settings.LOGOUT_REDIRECT_URL gesteuert
    #path('logout/', auth_views.LogoutView.as_view(template_name='members/login.html'), name='logout'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # NEU: Passwort ändern
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='members/password_change_form.html',
        success_url=reverse_lazy('password_change_done') #
 Weiterleitung nach Erfolg
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='members/password_change_done.html'
    ), name='password_change_done'),
]
