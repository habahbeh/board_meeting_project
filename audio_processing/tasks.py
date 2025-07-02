# audio_processing/tasks.py

import os
import tempfile
from django.conf import settings
from django.utils.translation import gettext as _
from transcription.models import Meeting, TranscriptSegment, MeetingReport
from speaker_identification.models import Speaker
from audio_processing.utils.preprocessing import convert_audio_to_wav, enhance_audio_quality
from speaker_identification.utils.diarization import perform_diarization, match_speakers_with_database
from transcription.utils.whisper_gpt4o import transcribe_with_whisper, enhance_transcript_with_gpt, \
    extract_decisions_and_tasks


def process_meeting_task(meeting_id):
    """
    معالجة الاجتماع
    """
    meeting = Meeting.objects.get(id=meeting_id)

    try:
        # التحقق من وضع الاختبار
        if getattr(settings, 'TESTING_MODE', False):
            # معالجة الاجتماع في وضع الاختبار
            process_meeting_in_testing_mode(meeting)
        else:
            # معالجة الاجتماع في الوضع العادي
            process_meeting_in_normal_mode(meeting)

    except Exception as e:
        # تسجيل الخطأ
        print(f"Error processing meeting {meeting_id}: {str(e)}")


def process_meeting_in_testing_mode(meeting):
    """
    معالجة الاجتماع في وضع الاختبار
    """
    import time

    # محاكاة وقت المعالجة
    time.sleep(5)

    # الحصول على المتحدثين المتاحين
    speakers = list(Speaker.objects.all())
    if not speakers:
        # إنشاء متحدث افتراضي إذا لم يوجد متحدثين
        default_speaker = Speaker.objects.create(
            name="متحدث افتراضي",
            position="غير معروف",
            speaker_type="unknown"
        )
        speakers = [default_speaker]

    # نصوص نموذجية للاختبار
    sample_texts = [
        "أهلاً بكم في اجتماع مجلس الإدارة. سنناقش اليوم نتائج الربع الثالث والميزانية التقديرية للربع الرابع.",
        "أود أن أشير إلى أن أرباح الربع الثالث تجاوزت التوقعات بنسبة 15% بفضل المبادرات التسويقية الجديدة.",
        "أقترح زيادة ميزانية التسويق للربع الرابع بنسبة 10% للاستفادة من هذا الزخم.",
        "أتفق مع هذا الاقتراح، ويجب أن نركز على المنتجات ذات هامش الربح الأعلى.",
        "قرار: الموافقة على زيادة ميزانية التسويق للربع الرابع بنسبة 10%.",
        "مهمة: يجب على أحمد تقديم خطة التسويق المحدثة خلال أسبوع.",
    ]

    # إنشاء المقاطع النصية
    start_time = 0
    for i, text in enumerate(sample_texts):
        end_time = start_time + 30  # كل مقطع 30 ثانية
        speaker_index = i % len(speakers)

        is_decision = "قرار" in text
        is_action_item = "مهمة" in text

        # إنشاء مقطع نصي
        TranscriptSegment.objects.create(
            meeting=meeting,
            speaker=speakers[speaker_index],
            start_time=start_time,
            end_time=end_time,
            text=text,
            confidence=0.95,
            is_decision=is_decision,
            is_action_item=is_action_item
        )

        start_time = end_time

    # إنشاء تقرير للاجتماع
    decisions = TranscriptSegment.objects.filter(meeting=meeting, is_decision=True)
    tasks = TranscriptSegment.objects.filter(meeting=meeting, is_action_item=True)

    MeetingReport.objects.create(
        meeting=meeting,
        summary="تم مناقشة نتائج الربع الثالث والميزانية التقديرية للربع الرابع. تم الاتفاق على زيادة ميزانية التسويق بنسبة 10%.",
        decisions="\n".join([d.text for d in decisions]),
        action_items="\n".join([t.text for t in tasks])
    )

    # تحديث حالة المعالجة
    meeting.processed = True
    meeting.save(update_fields=['processed'])
    print(f"Meeting {meeting.id} processing completed successfully.")


def process_meeting_in_normal_mode(meeting):
    """
    معالجة الاجتماع في الوضع العادي (مع API الحقيقي)
    """
    # إنشاء مجلد مؤقت لتخزين الملفات المعالجة
    temp_dir = tempfile.mkdtemp()

    try:
        # الحصول على مسار الملف الصوتي
        audio_path = os.path.join(settings.MEDIA_ROOT, str(meeting.audio_file))

        # تحويل الصوت إلى WAV وتحسين جودته
        print("تحويل وتحسين جودة الصوت...")
        wav_path = convert_audio_to_wav(audio_path, temp_dir)
        enhanced_path = enhance_audio_quality(wav_path, temp_dir)

        # إنشاء مقطع نصي واحد للاختبار
        print("نسخ الصوت باستخدام Whisper...")
        transcript_text = transcribe_with_whisper(enhanced_path)

        # تحسين النص باستخدام GPT
        print("تحسين النص باستخدام GPT...")
        enhanced_text = enhance_transcript_with_gpt(transcript_text)

        # استخراج القرارات والمهام
        print("استخراج القرارات والمهام...")
        decisions_tasks = extract_decisions_and_tasks(enhanced_text)

        # الحصول على المتحدثين المتاحين
        speakers = list(Speaker.objects.all())
        if not speakers:
            default_speaker = Speaker.objects.create(
                name="متحدث افتراضي",
                position="غير معروف",
                speaker_type="unknown"
            )
            speakers = [default_speaker]

        # إنشاء مقطع نصي واحد
        TranscriptSegment.objects.create(
            meeting=meeting,
            speaker=speakers[0],
            start_time=0,
            end_time=300,  # 5 دقائق
            text=enhanced_text,
            confidence=0.95,
            is_decision=False,
            is_action_item=False
        )

        # إنشاء تقرير للاجتماع
        MeetingReport.objects.create(
            meeting=meeting,
            summary=enhanced_text[:500] + "...",
            decisions=decisions_tasks,
            action_items=""
        )

        # تحديث حالة المعالجة
        meeting.processed = True
        meeting.save()

    finally:
        # تنظيف الملفات المؤقتة
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def process_meeting_in_testing_mode(meeting):
    """
    معالجة الاجتماع في وضع الاختبار
    """
    import time

    # تأخير لمحاكاة وقت المعالجة (مهم!)
    time.sleep(10)  # 10 ثوانٍ على الأقل

    # باقي كود المعالجة...

    # تحديث حالة المعالجة - مهم جداً!
    meeting.processed = True
    meeting.save(update_fields=['processed'])
    print(f"Meeting {meeting.id} processing completed successfully.")