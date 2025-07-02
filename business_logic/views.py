# business_logic/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from transcription.models import Meeting, TranscriptSegment

@login_required
def decisions_list(request):
    # استرجاع جميع القرارات من جميع الاجتماعات التي يملكها المستخدم
    meetings = Meeting.objects.filter(created_by=request.user, processed=True)
    decisions = TranscriptSegment.objects.filter(meeting__in=meetings, is_decision=True).order_by('-meeting__date')
    
    context = {
        'title': _('القرارات'),
        'decisions': decisions,
    }
    return render(request, 'business_logic/decisions_list.html', context)

@login_required
def tasks_list(request):
    # استرجاع جميع المهام من جميع الاجتماعات التي يملكها المستخدم
    meetings = Meeting.objects.filter(created_by=request.user, processed=True)
    tasks = TranscriptSegment.objects.filter(meeting__in=meetings, is_action_item=True).order_by('-meeting__date')
    
    context = {
        'title': _('المهام'),
        'tasks': tasks,
    }
    return render(request, 'business_logic/tasks_list.html', context)