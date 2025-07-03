# speaker_identification/admin.py

from django.contrib import admin
from .models import Speaker


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'speaker_type', 'has_voice_embedding', 'created_at']
    list_filter = ['speaker_type', 'created_at']
    search_fields = ['name', 'position']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('name', 'position', 'speaker_type')
        }),
        ('البيانات الصوتية', {
            'fields': ('reference_audio', 'voice_embedding'),
            'classes': ('collapse',)
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'voice_embedding']

    def has_voice_embedding(self, obj):
        return bool(obj.voice_embedding)

    has_voice_embedding.boolean = True
    has_voice_embedding.short_description = 'لديه بصمة صوتية'

    actions = ['generate_voice_embeddings']

    def generate_voice_embeddings(self, request, queryset):
        """إجراء لتوليد البصمات الصوتية للمتحدثين المحددين"""
        count = 0
        for speaker in queryset:
            if speaker.reference_audio:
                # هنا يمكن إضافة كود توليد البصمة الصوتية
                count += 1

        self.message_user(request, f'تم توليد {count} بصمة صوتية')

    generate_voice_embeddings.short_description = 'توليد البصمات الصوتية'