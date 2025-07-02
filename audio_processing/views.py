# audio_processing/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .forms import MeetingUploadForm
from transcription.models import Meeting
from .tasks import process_meeting_task
from django.http import JsonResponse
from django.conf import settings


@login_required
def upload_meeting(request):
    if request.method == 'POST':
        form = MeetingUploadForm(request.POST, request.FILES)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()
            
            messages.success(request, _('تم رفع الاجتماع بنجاح وسيتم معالجته قريبًا.'))
            return redirect('audio_processing:processing_status', meeting_id=meeting.id)
    else:
        form = MeetingUploadForm()
    
    context = {
        'title': _('رفع اجتماع جديد'),
        'form': form,
    }
    return render(request, 'audio_processing/upload_meeting.html', context)

# audio_processing/views.py

@login_required
def process_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)

    # بدء معالجة الاجتماع فوراً (بدون Celery للتبسيط)
    from .tasks import process_meeting_task
    process_meeting_task(meeting.id)
    
    messages.info(request, _('بدأت معالجة الاجتماع. سيستغرق ذلك بعض الوقت.'))
    return redirect('audio_processing:processing_status', meeting_id=meeting.id)

@login_required
def processing_status(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)
    
    context = {
        'title': _('حالة معالجة الاجتماع'),
        'meeting': meeting,
    }
    return render(request, 'audio_processing/processing_status.html', context)





@login_required
def check_processing_status(request, meeting_id):
    """
    التحقق من حالة معالجة الاجتماع وإرجاع النتيجة في صيغة JSON
    """
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)

    # في وضع الاختبار، نضيف تأخيراً اصطناعياً ثم نجعل المعالجة مكتملة
    if getattr(settings, 'TESTING_MODE', False) and not meeting.processed:
        # التحقق مما إذا مرت فترة كافية منذ بدء المعالجة (مثلاً 30 ثانية)
        import time
        from datetime import datetime, timedelta

        # افتراض أن وقت البدء هو وقت إنشاء الاجتماع أو آخر تحديث
        start_time = meeting.created_at
        current_time = datetime.now(start_time.tzinfo)

        # إذا مرت 30 ثانية، نجعل المعالجة مكتملة
        if (current_time - start_time) > timedelta(seconds=30):
            # استدعاء وظيفة المعالجة إذا لم تكن قد اكتملت بعد
            from .tasks import process_meeting_task
            process_meeting_task(meeting.id)

    return JsonResponse({
        'processed': meeting.processed,
        'id': meeting.id,
        'title': meeting.title,
    })