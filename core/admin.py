# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


# Inline للملف الشخصي
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'الملف الشخصي'


# تمديد User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# إلغاء تسجيل User الافتراضي وإعادة تسجيله مع الإضافات
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# تسجيل Profile منفصل أيضاً
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'job_title', 'department', 'phone']
    list_filter = ['department']
    search_fields = ['user__username', 'user__email', 'job_title', 'department']

    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user',)
        }),
        ('المعلومات الوظيفية', {
            'fields': ('job_title', 'department', 'phone')
        }),
    )