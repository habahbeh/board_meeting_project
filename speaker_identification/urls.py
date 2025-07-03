# speaker_identification/urls.py

from django.urls import path
from . import views

app_name = 'speaker_identification'

urlpatterns = [
    path('', views.speakers_list, name='speakers'),
    path('add/', views.add_speaker, name='add_speaker'),
    path('edit/<int:speaker_id>/', views.edit_speaker, name='edit_speaker'),
    path('delete/<int:speaker_id>/', views.delete_speaker, name='delete_speaker'),
    path('test-system/', views.test_speaker_system, name='test_speaker_system'),
]