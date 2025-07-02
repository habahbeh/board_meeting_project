# speaker_identification/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class Speaker(models.Model):
    SPEAKER_TYPES = (
        ('board', _('عضو مجلس إدارة')),
        ('executive', _('مدير تنفيذي')),
        ('visitor', _('زائر')),
        ('unknown', _('غير معروف')),
    )

    name = models.CharField(_('الاسم'), max_length=100)
    position = models.CharField(_('المنصب'), max_length=100)
    speaker_type = models.CharField(_('نوع المتحدث'), max_length=20, choices=SPEAKER_TYPES, default='board')
    voice_embedding = models.BinaryField(_('بصمة الصوت'), blank=True, null=True)
    reference_audio = models.FileField(_('ملف صوتي مرجعي'), upload_to='reference_audio/', blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('متحدث')
        verbose_name_plural = _('متحدثون')

    def __str__(self):
        return f"{self.name} - {self.position}"