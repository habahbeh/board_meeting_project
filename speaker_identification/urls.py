# speaker_identification/urls.py

from django.urls import path
from . import views
from .views_voice import (
    voice_comparison_dashboard,
    process_speaker_embedding,
    process_all_embeddings
)

app_name = 'speaker_identification'

urlpatterns = [
    path('', views.speakers_list, name='speakers'),
    path('add/', views.add_speaker, name='add_speaker'),
    path('edit/<int:speaker_id>/', views.edit_speaker, name='edit_speaker'),
    path('delete/<int:speaker_id>/', views.delete_speaker, name='delete_speaker'),
    path('test-system/', views.test_speaker_system, name='test_speaker_system'),
    path('voice-comparison/', voice_comparison_dashboard, name='voice_comparison'),
    path('process-embedding/', process_speaker_embedding, name='process_embedding'),
    path('process-all-embeddings/', process_all_embeddings, name='process_all_embeddings'),
]


