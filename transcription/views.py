# transcription/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils.translation import gettext as _
from .models import Meeting, TranscriptSegment, MeetingReport

@login_required
def meetings_list(request):
    meetings = Meeting.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'title': _('الاجتماعات'),
        'meetings': meetings,
    }
    return render(request, 'transcription/meetings_list.html', context)

@login_required
def view_meeting(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)
    segments = TranscriptSegment.objects.filter(meeting=meeting).order_by('start_time')
    
    context = {
        'title': meeting.title,
        'meeting': meeting,
        'segments': segments,
    }
    return render(request, 'transcription/view_meeting.html', context)

@login_required
def edit_transcript(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)
    segments = TranscriptSegment.objects.filter(meeting=meeting).order_by('start_time')
    
    if request.method == 'POST':
        # معالجة تحديث النصوص
        for key, value in request.POST.items():
            if key.startswith('segment_'):
                segment_id = int(key.replace('segment_', ''))
                segment = get_object_or_404(TranscriptSegment, id=segment_id, meeting=meeting)
                segment.text = value
                segment.save()
        
        messages.success(request, _('تم تحديث النص بنجاح.'))
        return redirect('transcription:view_meeting', meeting_id=meeting.id)
    
    context = {
        'title': _('تحرير نص الاجتماع'),
        'meeting': meeting,
        'segments': segments,
    }
    return render(request, 'transcription/edit_transcript.html', context)

@login_required
def meeting_report(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)
    
    try:
        report = MeetingReport.objects.get(meeting=meeting)
    except MeetingReport.DoesNotExist:
        report = None
    
    context = {
        'title': _('تقرير الاجتماع'),
        'meeting': meeting,
        'report': report,
    }
    return render(request, 'transcription/meeting_report.html', context)

@login_required
def export_transcript(request, meeting_id, format):
    meeting = get_object_or_404(Meeting, id=meeting_id, created_by=request.user)
    
    if format == 'pdf':
        # تصدير بصيغة PDF (هذا مثال بسيط)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{meeting.title}.pdf"'
        # هنا يجب إضافة كود إنشاء ملف PDF
        
        return response
    
    elif format == 'docx':
        # تصدير بصيغة DOCX (هذا مثال بسيط)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{meeting.title}.docx"'
        # هنا يجب إضافة كود إنشاء ملف DOCX
        
        return response
    
    elif format == 'json':
        # تصدير بصيغة JSON (هذا مثال بسيط)
        import json
        
        segments = TranscriptSegment.objects.filter(meeting=meeting).order_by('start_time')
        data = {
            'meeting': {
                'id': meeting.id,
                'title': meeting.title,
                'date': meeting.date.isoformat(),
            },
            'segments': [
                {
                    'id': segment.id,
                    'speaker': segment.speaker.name if segment.speaker else 'غير معروف',
                    'start_time': segment.start_time,
                    'end_time': segment.end_time,
                    'text': segment.text,
                    'is_decision': segment.is_decision,
                    'is_action_item': segment.is_action_item,
                }
                for segment in segments
            ]
        }
        
        response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{meeting.title}.json"'
        
        return response
    
    else:
        messages.error(request, _('صيغة التصدير غير مدعومة.'))
        return redirect('transcription:view_meeting', meeting_id=meeting.id)