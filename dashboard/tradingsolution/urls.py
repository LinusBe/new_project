"""
URL configuration for tradingsolution project.
 The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import
 include, path

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


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
