# core/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from transcription.models import Meeting, MeetingReport
from django.utils.translation import gettext as _

def home(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    
    context = {
        'title': _('الصفحة الرئيسية'),
    }
    return render(request, 'core/home.html', context)

@login_required
def dashboard(request):
    meetings = Meeting.objects.filter(created_by=request.user).order_by('-created_at')
    recent_meetings = meetings[:5]
    
    processing_count = meetings.filter(processed=False).count()
    completed_count = meetings.filter(processed=True).count()
    
    context = {
        'title': _('لوحة التحكم'),
        'recent_meetings': recent_meetings,
        'processing_count': processing_count,
        'completed_count': completed_count,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def profile(request):
    context = {
        'title': _('الملف الشخصي'),
    }
    return render(request, 'core/profile.html', context)