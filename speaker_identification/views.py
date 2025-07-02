# speaker_identification/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Speaker
from .forms import SpeakerForm

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