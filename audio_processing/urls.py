# audio_processing/urls.py

from django.urls import path
from . import views

app_name = 'audio_processing'

urlpatterns = [
    path('upload/', views.upload_meeting, name='upload_meeting'),
    path('process/<int:meeting_id>/', views.process_meeting, name='process_meeting'),
    path('status/<int:meeting_id>/', views.processing_status, name='processing_status'),
    path('check_status/<int:meeting_id>/', views.check_processing_status, name='check_status'),

]