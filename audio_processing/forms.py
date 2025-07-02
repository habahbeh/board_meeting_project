# audio_processing/forms.py

from django import forms
from transcription.models import Meeting
from django.utils.translation import gettext_lazy as _

class MeetingUploadForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['title', 'date', 'description', 'audio_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'audio_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': _('عنوان الاجتماع'),
            'date': _('تاريخ الاجتماع'),
            'description': _('وصف الاجتماع'),
            'audio_file': _('ملف التسجيل الصوتي'),
        }
        help_texts = {
            'audio_file': _('يدعم صيغ MP3, WAV, M4A - الحد الأقصى 3 ساعات'),
        }