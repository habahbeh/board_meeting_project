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
import threading


@login_required
def upload_meeting(request):
    if request.method == 'POST':
        form = MeetingUploadForm(request.POST, request.FILES)
        if form.is_valid():
            meeting = form.save(commit=False)
            meeting.created_by = request.user
            meeting.save()

            # بدء معالجة الاجتماع في خيط منفصل
            # هذا يسمح للمستخدم بمتابعة استخدام الموقع أثناء المعالجة
            thread = threading.Thread(target=process_meeting_task, args=(meeting.id,))
            thread.daemon = True
            thread.start()

            messages.success(request, _('تم رفع الاجتماع بنجاح وسيتم معالجته قريبًا.'))
            return redirect('audio_processing:processing_status', meeting_id=meeting.id)
    else:
        form = MeetingUploadForm()

    context = {
        'title': _('رفع اجتماع جديد'),
        'form': form,
    }
    return render(request, 'audio_processing/upload_meeting.html', context)


@login_required
def process_meeting(request, meeting_id):
    """
    بدء معالجة اجتماع موجود
    """
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)

    if not meeting.processed:
        # بدء معالجة الاجتماع في خيط منفصل
        thread = threading.Thread(target=process_meeting_task, args=(meeting.id,))
        thread.daemon = True
        thread.start()

        messages.info(request, _('بدأت معالجة الاجتماع. سيستغرق ذلك بعض الوقت.'))
    else:
        messages.warning(request, _('تمت معالجة هذا الاجتماع بالفعل.'))

    return redirect('audio_processing:processing_status', meeting_id=meeting.id)


@login_required
def processing_status(request, meeting_id):
    """
    عرض حالة معالجة الاجتماع
    """
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
    يستخدم من JavaScript للتحقق الدوري من حالة المعالجة
    """
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)

    # إعادة قراءة حالة الاجتماع من قاعدة البيانات للحصول على آخر تحديث
    meeting.refresh_from_db()

    return JsonResponse({
        'processed': meeting.processed,
        'id': meeting.id,
        'title': meeting.title,
    })