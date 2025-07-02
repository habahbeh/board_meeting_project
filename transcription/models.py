# transcription/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from speaker_identification.models import Speaker


class Meeting(models.Model):
    title = models.CharField(_('عنوان الاجتماع'), max_length=200)
    date = models.DateField(_('تاريخ الاجتماع'))
    description = models.TextField(_('وصف الاجتماع'), blank=True)
    audio_file = models.FileField(_('ملف التسجيل الصوتي'), upload_to='meeting_audio/')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_meetings')
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    processed = models.BooleanField(_('تمت المعالجة'), default=False)

    class Meta:
        verbose_name = _('اجتماع')
        verbose_name_plural = _('اجتماعات')

    def __str__(self):
        return f"{self.title} - {self.date}"


class TranscriptSegment(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='segments')
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True, related_name='segments')
    start_time = models.FloatField(_('وقت البداية (بالثواني)'))
    end_time = models.FloatField(_('وقت النهاية (بالثواني)'))
    text = models.TextField(_('النص'))
    confidence = models.FloatField(_('نسبة الثقة'), default=0.0)
    is_personal = models.BooleanField(_('محادثة شخصية'), default=False)
    is_decision = models.BooleanField(_('قرار'), default=False)
    is_action_item = models.BooleanField(_('مهمة'), default=False)

    class Meta:
        verbose_name = _('مقطع نصي')
        verbose_name_plural = _('مقاطع نصية')
        ordering = ['start_time']

    def __str__(self):
        return f"{self.meeting.title} - {self.speaker.name if self.speaker else 'غير معروف'} - {self.start_time:.2f}s-{self.end_time:.2f}s"


class MeetingReport(models.Model):
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='report')
    summary = models.TextField(_('ملخص الاجتماع'))
    decisions = models.TextField(_('القرارات'))
    action_items = models.TextField(_('المهام'))
    generated_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('تقرير اجتماع')
        verbose_name_plural = _('تقارير اجتماعات')

    def __str__(self):
        return f"تقرير - {self.meeting.title}"