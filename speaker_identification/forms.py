# speaker_identification/forms.py

from django import forms
from .models import Speaker
from django.utils.translation import gettext_lazy as _

class SpeakerForm(forms.ModelForm):
    class Meta:
        model = Speaker
        fields = ['name', 'position', 'speaker_type', 'reference_audio']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'speaker_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_audio': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _('الاسم'),
            'position': _('المنصب'),
            'speaker_type': _('نوع المتحدث'),
            'reference_audio': _('ملف صوتي مرجعي'),
        }
        help_texts = {
            'reference_audio': _('ملف صوتي يحتوي على صوت المتحدث فقط (30 ثانية على الأقل)'),
        }