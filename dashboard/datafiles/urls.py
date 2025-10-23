from django.urls import path
from . import views

# Define an app_name for namespacing (z.B. {% url 'datafiles:download' %})
app_name = 'datafiles'

# URLs sind unter /files/ erreichbar (siehe solutiontrading/urls.py)
urlpatterns = [
    path('<int:file_id>/download/', views.download_file, name='download'),
    path('<int:file_id>/analyze/', views.analyze_file, name='analyze'),
]
