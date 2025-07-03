# business_logic/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Q
from transcription.models import TranscriptSegment, Meeting


# عرض مخصص للقرارات
class DecisionAdmin(admin.ModelAdmin):
    """
    عرض إداري للقرارات المستخرجة من الاجتماعات
    """
    model = TranscriptSegment
    list_display = ['decision_text', 'meeting_link', 'speaker', 'decision_date', 'view_context']
    list_filter = ['meeting__date', 'speaker', 'meeting']
    search_fields = ['text', 'meeting__title', 'speaker__name']
    date_hierarchy = 'meeting__date'

    def get_queryset(self, request):
        # فقط المقاطع المحددة كقرارات
        qs = super().get_queryset(request)
        return qs.filter(is_decision=True)

    def decision_text(self, obj):
        return obj.text[:150] + '...' if len(obj.text) > 150 else obj.text

    decision_text.short_description = 'نص القرار'

    def meeting_link(self, obj):
        return format_html(
            '<a href="/admin/transcription/meeting/{}/change/">{}</a>',
            obj.meeting.id,
            obj.meeting.title
        )

    meeting_link.short_description = 'الاجتماع'

    def decision_date(self, obj):
        return obj.meeting.date

    decision_date.short_description = 'تاريخ القرار'
    decision_date.admin_order_field = 'meeting__date'

    def view_context(self, obj):
        from django.urls import reverse
        url = reverse('transcription:view_meeting', args=[obj.meeting.id])
        return format_html(
            '<a href="{}#segment-{}" target="_blank">عرض السياق</a>',
            url, obj.id
        )

    view_context.short_description = 'السياق'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Meta:
        verbose_name = 'قرار'
        verbose_name_plural = 'القرارات'


# عرض مخصص للمهام
class TaskAdmin(admin.ModelAdmin):
    """
    عرض إداري للمهام المستخرجة من الاجتماعات
    """
    model = TranscriptSegment
    list_display = ['task_text', 'assignee', 'meeting_link', 'task_date', 'status', 'view_context']
    list_filter = ['meeting__date', 'speaker', 'meeting']
    search_fields = ['text', 'meeting__title', 'speaker__name']
    date_hierarchy = 'meeting__date'

    def get_queryset(self, request):
        # فقط المقاطع المحددة كمهام
        qs = super().get_queryset(request)
        return qs.filter(is_action_item=True)

    def task_text(self, obj):
        return obj.text[:150] + '...' if len(obj.text) > 150 else obj.text

    task_text.short_description = 'نص المهمة'

    def assignee(self, obj):
        # محاولة استخراج المكلف من النص
        text = obj.text
        if 'نكلف' in text:
            words = text.split('نكلف')[1].split()
            if words:
                return ' '.join(words[:2])
        elif 'مهمة ل' in text:
            words = text.split('مهمة ل')[1].split()
            if words:
                return ' '.join(words[:2])
        return obj.speaker.name if obj.speaker else 'غير محدد'

    assignee.short_description = 'المكلف'

    def meeting_link(self, obj):
        return format_html(
            '<a href="/admin/transcription/meeting/{}/change/">{}</a>',
            obj.meeting.id,
            obj.meeting.title
        )

    meeting_link.short_description = 'الاجتماع'

    def task_date(self, obj):
        return obj.meeting.date

    task_date.short_description = 'تاريخ التكليف'
    task_date.admin_order_field = 'meeting__date'

    def status(self, obj):
        # يمكن تطوير هذا لاحقاً لتتبع حالة المهام
        return format_html(
            '<span style="color: orange;">⏳ قيد التنفيذ</span>'
        )

    status.short_description = 'الحالة'

    def view_context(self, obj):
        from django.urls import reverse
        url = reverse('transcription:view_meeting', args=[obj.meeting.id])
        return format_html(
            '<a href="{}#segment-{}" target="_blank">عرض السياق</a>',
            url, obj.id
        )

    view_context.short_description = 'السياق'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    actions = ['mark_as_completed', 'export_tasks']

    def mark_as_completed(self, request, queryset):
        # يمكن تطوير هذا لاحقاً لتتبع إنجاز المهام
        self.message_user(request, 'سيتم إضافة ميزة تتبع المهام قريباً')

    mark_as_completed.short_description = 'تحديد كمنجز'

    def export_tasks(self, request, queryset):
        # يمكن تطوير هذا لتصدير المهام
        self.message_user(request, 'سيتم إضافة ميزة التصدير قريباً')

    export_tasks.short_description = 'تصدير المهام'

    class Meta:
        verbose_name = 'مهمة'
        verbose_name_plural = 'المهام'


# إحصائيات الأعمال
class BusinessStatisticsAdmin(admin.ModelAdmin):
    """
    لوحة إحصائيات للقرارات والمهام
    """
    change_list_template = 'admin/business_statistics.html'

    def changelist_view(self, request, extra_context=None):
        # إحصائيات القرارات
        decisions_count = TranscriptSegment.objects.filter(is_decision=True).count()
        decisions_by_month = TranscriptSegment.objects.filter(
            is_decision=True
        ).extra(
            select={'month': "strftime('%%Y-%%m', meeting__date)"}
        ).values('month').annotate(count=models.Count('id'))

        # إحصائيات المهام
        tasks_count = TranscriptSegment.objects.filter(is_action_item=True).count()
        tasks_by_speaker = TranscriptSegment.objects.filter(
            is_action_item=True
        ).values('speaker__name').annotate(count=models.Count('id'))

        # إحصائيات الاجتماعات
        meetings_count = Meeting.objects.filter(processed=True).count()

        extra_context = extra_context or {}
        extra_context.update({
            'decisions_count': decisions_count,
            'tasks_count': tasks_count,
            'meetings_count': meetings_count,
            'decisions_by_month': list(decisions_by_month),
            'tasks_by_speaker': list(tasks_by_speaker),
        })

        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    class Meta:
        verbose_name = 'إحصائيات الأعمال'
        verbose_name_plural = 'إحصائيات الأعمال'

# تسجيل النماذج الإدارية
# admin.site.register(TranscriptSegment, DecisionAdmin)
# admin.site.register(TranscriptSegment, TaskAdmin)