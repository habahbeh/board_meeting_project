# audio_processing/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .forms import MeetingUploadForm
from transcription.models import Meeting
# from .tasks import process_meeting_task
from .tasks_enhanced import process_meeting_task

from django.http import JsonResponse
from django.conf import settings
import threading
from django.http import JsonResponse
import openai
import os

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


@login_required
def debug_openai(request):
    """
    صفحة تشخيص مشاكل OpenAI
    """
    debug_info = {
        'settings': {
            'TESTING_MODE': getattr(settings, 'TESTING_MODE', None),
            'OPENAI_API_KEY_exists': bool(getattr(settings, 'OPENAI_API_KEY', None)),
            'OPENAI_API_KEY_preview': settings.OPENAI_API_KEY[:10] + '...' if settings.OPENAI_API_KEY else 'NOT SET',
        },
        'tests': {}
    }

    # اختبار GPT
    try:
        openai.api_key = settings.OPENAI_API_KEY
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10
        )
        debug_info['tests']['gpt'] = "✓ يعمل"
    except Exception as e:
        debug_info['tests']['gpt'] = f"❌ خطأ: {str(e)}"

    # اختبار وجود ملفات صوتية
    media_path = os.path.join(settings.MEDIA_ROOT, 'meeting_audio')
    if os.path.exists(media_path):
        audio_files = [f for f in os.listdir(media_path) if f.endswith(('.mp3', '.wav'))]
        debug_info['audio_files'] = audio_files[:5]  # أول 5 ملفات
    else:
        debug_info['audio_files'] = []

    # قراءة آخر الأخطاء من السجل
    log_file = os.path.join(settings.LOGS_DIR, 'debug.log')
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # آخر 20 سطر يحتوي على ERROR
            errors = [line.strip() for line in lines if 'ERROR' in line][-20:]
            debug_info['recent_errors'] = errors

    return JsonResponse(debug_info, json_dumps_params={'ensure_ascii': False, 'indent': 2})
