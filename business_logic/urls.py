# business_logic/urls.py

from django.urls import path
from . import views

app_name = 'business_logic'

urlpatterns = [
    path('decisions/', views.decisions_list, name='decisions'),
    path('tasks/', views.tasks_list, name='tasks'),
]