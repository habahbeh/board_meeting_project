# speaker_identification/views_voice.py - إضافة للـ views الموجودة

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from .models import Speaker
from transcription.models import Meeting
from .utils.voice_comparison import save_speaker_embedding


@login_required
def voice_comparison_dashboard(request):
    """لوحة تحكم المقارنة الصوتية"""
    context = {
        'title': 'نظام المقارنة الصوتية',

        # حالة النظام
        'has_hf_token': bool(os.getenv("HUGGINGFACE_TOKEN")),
        'has_pytorch': check_pytorch_installed(),
        'has_pyannote': check_pyannote_installed(),
        'cuda_available': check_cuda_available(),

        # إحصائيات المتحدثين
        'total_speakers': Speaker.objects.count(),
        'speakers_with_audio': Speaker.objects.filter(reference_audio__isnull=False).count(),
        'speakers_with_embeddings': Speaker.objects.filter(voice_embedding__isnull=False).count(),

        # قائمة المتحدثين
        'speakers': Speaker.objects.all().order_by('name'),

        # المتحدثين الذين يحتاجون معالجة
        'speakers_needing_processing': Speaker.objects.filter(
            reference_audio__isnull=False,
            voice_embedding__isnull=True
        ).count(),

        # الاجتماعات غير المعالجة
        'unprocessed_meetings': Meeting.objects.filter(
            processed=False,
            created_by=request.user
        ).order_by('-date')
    }

    return render(request, 'speaker_identification/voice_comparison.html', context)


@login_required
def process_speaker_embedding(request):
    """معالجة بصمة صوتية لمتحدث واحد"""
    if request.method == 'POST':
        speaker_id = request.POST.get('speaker_id')

        try:
            speaker = Speaker.objects.get(id=speaker_id)

            if not speaker.reference_audio:
                return JsonResponse({'success': False, 'error': 'لا يوجد ملف صوتي'})

            # معالجة البصمة
            if save_speaker_embedding(speaker):
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'فشل إنشاء البصمة'})

        except Speaker.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'المتحدث غير موجود'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'طلب غير صالح'})


@login_required
def process_all_embeddings(request):
    """معالجة جميع البصمات المتبقية"""
    if request.method == 'POST':
        speakers = Speaker.objects.filter(
            reference_audio__isnull=False,
            voice_embedding__isnull=True
        )

        processed = 0
        errors = []

        for speaker in speakers:
            try:
                if save_speaker_embedding(speaker):
                    processed += 1
                else:
                    errors.append(f"فشل مع {speaker.name}")
            except Exception as e:
                errors.append(f"{speaker.name}: {str(e)}")

        return JsonResponse({
            'success': True,
            'processed': processed,
            'errors': errors
        })

    return JsonResponse({'success': False, 'error': 'طلب غير صالح'})


def check_pytorch_installed():
    """التحقق من تثبيت PyTorch"""
    try:
        import torch
        return True
    except ImportError:
        return False


def check_pyannote_installed():
    """التحقق من تثبيت pyannote"""
    try:
        import pyannote.audio
        return True
    except ImportError:
        return False


def check_cuda_available():
    """التحقق من توفر GPU"""
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False


