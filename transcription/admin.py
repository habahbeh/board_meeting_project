# transcription/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Meeting, TranscriptSegment, MeetingReport


# Inline للمقاطع النصية
class TranscriptSegmentInline(admin.TabularInline):
    model = TranscriptSegment
    extra = 0
    fields = ['speaker', 'start_time', 'end_time', 'text', 'is_decision', 'is_action_item']
    readonly_fields = ['start_time', 'end_time']
    can_delete = False


# Inline للتقرير
class MeetingReportInline(admin.StackedInline):
    model = MeetingReport
    extra = 0
    fields = ['summary', 'decisions', 'action_items', 'generated_at']
    readonly_fields = ['generated_at']
    can_delete = False


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'created_by', 'processed', 'created_at', 'view_transcript_link']
    list_filter = ['processed', 'date', 'created_at']
    search_fields = ['title', 'description', 'created_by__username']
    date_hierarchy = 'date'
    inlines = [MeetingReportInline, TranscriptSegmentInline]

    fieldsets = (
        ('معلومات الاجتماع', {
            'fields': ('title', 'date', 'description')
        }),
        ('الملف الصوتي', {
            'fields': ('audio_file',)
        }),
        ('حالة المعالجة', {
            'fields': ('processed', 'created_by', 'created_at'),
        }),
    )

    readonly_fields = ['created_at', 'created_by']

    def view_transcript_link(self, obj):
        if obj.processed:
            url = reverse('transcription:view_meeting', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">عرض النص</a>', url)
        return '-'

    view_transcript_link.short_description = 'عرض النص'

    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    actions = ['mark_as_processed', 'mark_as_unprocessed', 'reprocess_meetings']

    def mark_as_processed(self, request, queryset):
        count = queryset.update(processed=True)
        self.message_user(request, f'تم تحديد {count} اجتماع كمعالج')

    mark_as_processed.short_description = 'تحديد كمعالج'

    def mark_as_unprocessed(self, request, queryset):
        count = queryset.update(processed=False)
        self.message_user(request, f'تم تحديد {count} اجتماع كغير معالج')

    mark_as_unprocessed.short_description = 'تحديد كغير معالج'

    def reprocess_meetings(self, request, queryset):
        from audio_processing.tasks import process_meeting_task
        import threading

        count = 0
        for meeting in queryset:
            thread = threading.Thread(target=process_meeting_task, args=(meeting.id,))
            thread.daemon = True
            thread.start()
            count += 1

        self.message_user(request, f'تم بدء إعادة معالجة {count} اجتماع')

    reprocess_meetings.short_description = 'إعادة معالجة'


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'speaker', 'start_time', 'end_time', 'text_preview',
                    'is_decision', 'is_action_item', 'is_personal', 'confidence']
    list_filter = ['is_decision', 'is_action_item', 'is_personal', 'meeting', 'speaker']
    search_fields = ['text', 'meeting__title', 'speaker__name']
    list_editable = ['is_decision', 'is_action_item', 'is_personal']

    fieldsets = (
        ('معلومات المقطع', {
            'fields': ('meeting', 'speaker', 'start_time', 'end_time')
        }),
        ('المحتوى', {
            'fields': ('text', 'confidence')
        }),
        ('التصنيفات', {
            'fields': ('is_decision', 'is_action_item', 'is_personal')
        }),
    )

    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text

    text_preview.short_description = 'النص'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # فقط الاجتماعات التي أنشأها المستخدم
        if not request.user.is_superuser:
            qs = qs.filter(meeting__created_by=request.user)
        return qs


@admin.register(MeetingReport)
class MeetingReportAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'generated_at', 'has_decisions', 'has_action_items']
    list_filter = ['generated_at']
    search_fields = ['meeting__title', 'summary', 'decisions', 'action_items']
    date_hierarchy = 'generated_at'

    fieldsets = (
        ('الاجتماع', {
            'fields': ('meeting',)
        }),
        ('الملخص', {
            'fields': ('summary',)
        }),
        ('القرارات والمهام', {
            'fields': ('decisions', 'action_items')
        }),
        ('معلومات الإنشاء', {
            'fields': ('generated_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['generated_at']

    def has_decisions(self, obj):
        return bool(obj.decisions and obj.decisions.strip())

    has_decisions.boolean = True
    has_decisions.short_description = 'يحتوي قرارات'

    def has_action_items(self, obj):
        return bool(obj.action_items and obj.action_items.strip())

    has_action_items.boolean = True
    has_action_items.short_description = 'يحتوي مهام'