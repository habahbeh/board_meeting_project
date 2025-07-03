# speaker_identification/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Speaker
from .forms import SpeakerForm
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .utils.voice_embeddings import test_voice_embedding
from .utils.diarization import test_speaker_recognition
import os

@staff_member_required
def test_speaker_system(request):
    """
    صفحة اختبار نظام التعرف على المتحدثين
    """
    results = {
        'status': 'testing',
        'tests': {}
    }

    # اختبار 1: التحقق من المكتبات
    try:
        import pyannote.audio
        import speechbrain
        import torch
        results['tests']['libraries'] = {
            'status': 'success',
            'message': 'جميع المكتبات مثبتة',
            'details': {
                'pyannote': pyannote.audio.__version__,
                'speechbrain': speechbrain.__version__,
                'torch': torch.__version__,
                'cuda_available': torch.cuda.is_available()
            }
        }
    except ImportError as e:
        results['tests']['libraries'] = {
            'status': 'error',
            'message': f'مكتبة مفقودة: {str(e)}'
        }

    # اختبار 2: Hugging Face Token
    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if hf_token:
        results['tests']['huggingface'] = {
            'status': 'success',
            'message': 'Hugging Face token موجود',
            'token_preview': f'{hf_token[:10]}...{hf_token[-4:]}'
        }
    else:
        results['tests']['huggingface'] = {
            'status': 'error',
            'message': 'HUGGINGFACE_TOKEN غير موجود في .env'
        }

    # اختبار 3: المتحدثين والبصمات الصوتية
    from .models import Speaker
    speakers_total = Speaker.objects.count()
    speakers_with_audio = Speaker.objects.filter(reference_audio__isnull=False).count()
    speakers_with_embeddings = Speaker.objects.filter(voice_embedding__isnull=False).count()

    results['tests']['speakers'] = {
        'status': 'info',
        'total': speakers_total,
        'with_audio': speakers_with_audio,
        'with_embeddings': speakers_with_embeddings,
        'message': f'{speakers_with_embeddings}/{speakers_with_audio} متحدث لديهم بصمات صوتية'
    }

    # اختبار 4: البصمات الصوتية
    if request.GET.get('test_embedding') == '1':
        try:
            if test_voice_embedding():
                results['tests']['embedding'] = {
                    'status': 'success',
                    'message': 'اختبار البصمة الصوتية نجح'
                }
            else:
                results['tests']['embedding'] = {
                    'status': 'warning',
                    'message': 'لا يوجد متحدثين بملفات صوتية للاختبار'
                }
        except Exception as e:
            results['tests']['embedding'] = {
                'status': 'error',
                'message': f'فشل اختبار البصمة: {str(e)}'
            }

    # اختبار 5: Speaker Recognition الكامل
    if request.GET.get('test_recognition') == '1':
        try:
            if test_speaker_recognition():
                results['tests']['recognition'] = {
                    'status': 'success',
                    'message': 'اختبار التعرف على المتحدثين نجح'
                }
            else:
                results['tests']['recognition'] = {
                    'status': 'warning',
                    'message': 'لا يوجد ملفات صوتية للاختبار'
                }
        except Exception as e:
            results['tests']['recognition'] = {
                'status': 'error',
                'message': f'فشل اختبار التعرف: {str(e)}'
            }

    # الحالة العامة
    has_errors = any(
        test.get('status') == 'error'
        for test in results['tests'].values()
    )
    results['status'] = 'error' if has_errors else 'success'

    return JsonResponse(results, json_dumps_params={'ensure_ascii': False, 'indent': 2})



@login_required
def speakers_list(request):
    speakers = Speaker.objects.all()
    context = {
        'title': _('المتحدثون'),
        'speakers': speakers,
    }
    return render(request, 'speaker_identification/speakers_list.html', context)

@login_required
def add_speaker(request):
    if request.method == 'POST':
        form = SpeakerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, _('تمت إضافة المتحدث بنجاح.'))
            return redirect('speaker_identification:speakers')
    else:
        form = SpeakerForm()
    
    context = {
        'title': _('إضافة متحدث جديد'),
        'form': form,
    }
    return render(request, 'speaker_identification/speaker_form.html', context)

@login_required
def edit_speaker(request, speaker_id):
    speaker = get_object_or_404(Speaker, id=speaker_id)
    
    if request.method == 'POST':
        form = SpeakerForm(request.POST, request.FILES, instance=speaker)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث بيانات المتحدث بنجاح.'))
            return redirect('speaker_identification:speakers')
    else:
        form = SpeakerForm(instance=speaker)
    
    context = {
        'title': _('تعديل بيانات المتحدث'),
        'form': form,
        'speaker': speaker,
    }
    return render(request, 'speaker_identification/speaker_form.html', context)

@login_required
def delete_speaker(request, speaker_id):
    speaker = get_object_or_404(Speaker, id=speaker_id)
    
    if request.method == 'POST':
        speaker.delete()
        messages.success(request, _('تم حذف المتحدث بنجاح.'))
        return redirect('speaker_identification:speakers')
    
    context = {
        'title': _('حذف المتحدث'),
        'speaker': speaker,
    }
    return render(request, 'speaker_identification/speaker_confirm_delete.html', context)