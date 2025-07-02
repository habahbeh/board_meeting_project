# core/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    job_title = models.CharField(_('المسمى الوظيفي'), max_length=100, blank=True)
    department = models.CharField(_('القسم/الإدارة'), max_length=100, blank=True)
    phone = models.CharField(_('رقم الهاتف'), max_length=20, blank=True)

    class Meta:
        verbose_name = _('الملف الشخصي')
        verbose_name_plural = _('الملفات الشخصية')

    def __str__(self):
        return f"{self.user.username} - {self.job_title}"