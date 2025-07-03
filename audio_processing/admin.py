# audio_processing/admin.py

from django.contrib import admin
from django.utils.html import format_html
from transcription.models import Meeting


# نضع تكوين Meeting هنا إذا أردنا عرضه من منظور معالجة الصوت
class AudioProcessingMeetingAdmin(admin.ModelAdmin):
    """
    عرض مخصص للاجتماعات من منظور معالجة الصوت
    """
    list_display = ['title', 'audio_file_info', 'processing_status', 'processing_actions']
    list_filter = ['processed', 'created_at']
    search_fields = ['title', 'audio_file']

    fieldsets = (
        ('ملف الصوت', {
            'fields': ('title', 'audio_file', 'audio_file_info_display')
        }),
        ('حالة المعالجة', {
            'fields': ('processed', 'created_at')
        }),
    )

    readonly_fields = ['audio_file_info_display', 'created_at', 'processed']

    def audio_file_info(self, obj):
        if obj.audio_file:
            size_mb = obj.audio_file.size / (1024 * 1024)
            return format_html(
                '<span>{}<br><small>{:.2f} MB</small></span>',
                obj.audio_file.name.split('/')[-1],
                size_mb
            )
        return '-'

    audio_file_info.short_description = 'معلومات الملف'

    def audio_file_info_display(self, obj):
        if obj.audio_file:
            size_mb = obj.audio_file.size / (1024 * 1024)
            return format_html(
                '''
                <div style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
                    <strong>اسم الملف:</strong> {}<br>
                    <strong>الحجم:</strong> {:.2f} MB<br>
                    <strong>المسار:</strong> {}
                </div>
                ''',
                obj.audio_file.name.split('/')[-1],
                size_mb,
                obj.audio_file.url
            )
        return 'لا يوجد ملف'

    audio_file_info_display.short_description = 'تفاصيل الملف الصوتي'

    def processing_status(self, obj):
        if obj.processed:
            return format_html(
                '<span style="color: green;">✓ تمت المعالجة</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">⏳ في انتظار المعالجة</span>'
            )

    processing_status.short_description = 'الحالة'

    def processing_actions(self, obj):
        from django.urls import reverse

        if obj.processed:
            url = reverse('transcription:view_meeting', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" target="_blank">عرض النص</a>',
                url
            )
        else:
            url = reverse('audio_processing:process_meeting', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button">بدء المعالجة</a>',
                url
            )

    processing_actions.short_description = 'الإجراءات'

    def has_add_permission(self, request):
        # منع الإضافة من هنا، يجب استخدام واجهة الرفع
        return False

    def has_delete_permission(self, request, obj=None):
        # السماح بالحذف فقط للمشرفين
        return request.user.is_superuser

    actions = ['process_selected_meetings']

    def process_selected_meetings(self, request, queryset):
        from audio_processing.tasks import process_meeting_task
        import threading

        unprocessed = queryset.filter(processed=False)
        count = 0

        for meeting in unprocessed:
            thread = threading.Thread(target=process_meeting_task, args=(meeting.id,))
            thread.daemon = True
            thread.start()
            count += 1

        if count:
            self.message_user(request, f'تم بدء معالجة {count} اجتماع')
        else:
            self.message_user(request, 'جميع الاجتماعات المحددة تمت معالجتها بالفعل')

    process_selected_meetings.short_description = 'معالجة الاجتماعات المحددة'

# تسجيل نموذج Meeting مع تكوين مخصص لمعالجة الصوت
# admin.site.register(Meeting, AudioProcessingMeetingAdmin)