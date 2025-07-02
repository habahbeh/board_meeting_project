# transcription/urls.py
# تأكد من أن أنماط URL تتطابق مع ما هو مستخدم في القوالب

from django.urls import path
from . import views

app_name = 'transcription'

urlpatterns = [
    path('', views.meetings_list, name='meetings'),
    path('view/<int:meeting_id>/', views.view_meeting, name='view_meeting'),  # تأكد من هذا النمط
    path('edit/<int:meeting_id>/', views.edit_transcript, name='edit_transcript'),
    path('report/<int:meeting_id>/', views.meeting_report, name='meeting_report'),
    path('export/<int:meeting_id>/<str:format>/', views.export_transcript, name='export_transcript'),
]