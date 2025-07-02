# audio_processing/tasks.py

import os
import tempfile
import time
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
        meeting.processed = False
        meeting.save()


def process_meeting_in_testing_mode(meeting):
    """
    معالجة الاجتماع في وضع الاختبار
    """
    print(f"Starting test processing for meeting {meeting.id}")

    # محاكاة وقت المعالجة (مهم لواقعية التجربة)
    delay = getattr(settings, 'SIMULATION_DELAY', 30)
    print(f"Simulating processing delay of {delay} seconds...")
    time.sleep(delay)

    # الحصول على المتحدثين المتاحين
    speakers = list(Speaker.objects.all())
    if not speakers:
        # إنشاء متحدثين افتراضيين إذا لم يوجد متحدثين
        print("Creating default speakers...")
        speakers = [
            Speaker.objects.create(
                name="د. أحمد محمد",
                position="رئيس مجلس الإدارة",
                speaker_type="board"
            ),
            Speaker.objects.create(
                name="م. فاطمة علي",
                position="المدير التنفيذي",
                speaker_type="executive"
            ),
            Speaker.objects.create(
                name="أ. سارة خالد",
                position="المدير المالي",
                speaker_type="executive"
            ),
        ]

    # نصوص نموذجية للاختبار (أكثر واقعية)
    sample_texts = [
        "أهلاً بكم في اجتماع مجلس الإدارة. سنناقش اليوم نتائج الربع الثالث والميزانية التقديرية للربع الرابع.",
        "أود أن أشير إلى أن أرباح الربع الثالث تجاوزت التوقعات بنسبة 15% بفضل المبادرات التسويقية الجديدة.",
        "أقترح زيادة ميزانية التسويق للربع الرابع بنسبة 10% للاستفادة من هذا الزخم.",
        "أتفق مع هذا الاقتراح، ويجب أن نركز على المنتجات ذات هامش الربح الأعلى.",
        "بناءً على المناقشة، نصدر القرار التالي: الموافقة على زيادة ميزانية التسويق للربع الرابع بنسبة 10%.",
        "كما نكلف أحمد بمهمة تقديم خطة التسويق المحدثة خلال أسبوع من تاريخه.",
        "الآن ننتقل لمناقشة تقرير الموارد البشرية حول خطة التوظيف للعام القادم.",
        "نحتاج إلى توظيف 50 موظف جديد في قسم التطوير التقني لدعم خطط التوسع.",
        "القرار الثاني: الموافقة على خطة التوظيف المقترحة مع ميزانية قدرها 5 ملايين ريال.",
        "مهمة لفاطمة: إعداد جدول زمني مفصل لعملية التوظيف وتقديمه في الاجتماع القادم.",
    ]

    # إنشاء المقاطع النصية
    print("Creating transcript segments...")
    start_time = 0
    for i, text in enumerate(sample_texts):
        end_time = start_time + 30  # كل مقطع 30 ثانية
        speaker_index = i % len(speakers)

        is_decision = "القرار" in text or "نصدر القرار" in text
        is_action_item = "مهمة" in text or "نكلف" in text

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
    print("Creating meeting report...")
    decisions = TranscriptSegment.objects.filter(meeting=meeting, is_decision=True)
    tasks = TranscriptSegment.objects.filter(meeting=meeting, is_action_item=True)

    summary = """
    تم عقد اجتماع مجلس الإدارة لمناقشة نتائج الربع الثالث وخطط الربع الرابع. 
    أظهرت النتائج تحسناً ملحوظاً في الأداء مع تجاوز الأرباح للتوقعات بنسبة 15%.
    تمت مناقشة خطط التسويق وخطة التوظيف للعام القادم.
    """

    decisions_text = "\n".join([f"- {d.text}" for d in decisions])
    tasks_text = "\n".join([f"- {t.text}" for t in tasks])

    MeetingReport.objects.create(
        meeting=meeting,
        summary=summary.strip(),
        decisions=decisions_text or "لا توجد قرارات مسجلة",
        action_items=tasks_text or "لا توجد مهام مسجلة"
    )

    # تحديث حالة المعالجة - مهم جداً!
    meeting.processed = True
    meeting.save(update_fields=['processed'])
    print(f"Meeting {meeting.id} processing completed successfully.")


def process_meeting_in_normal_mode(meeting):
    """
    معالجة الاجتماع في الوضع العادي (مع API الحقيقي)
    """
    print(f"Starting real processing for meeting {meeting.id}")

    # إنشاء مجلد مؤقت لتخزين الملفات المعالجة
    temp_dir = tempfile.mkdtemp()

    try:
        # الحصول على مسار الملف الصوتي
        audio_path = os.path.join(settings.MEDIA_ROOT, str(meeting.audio_file))

        # تحويل الصوت إلى WAV وتحسين جودته
        print("Converting and enhancing audio...")
        wav_path = convert_audio_to_wav(audio_path, temp_dir)
        enhanced_path = enhance_audio_quality(wav_path, temp_dir)

        # نسخ الصوت باستخدام Whisper
        print("Transcribing with Whisper...")
        transcript_text = transcribe_with_whisper(enhanced_path)

        # تحسين النص باستخدام GPT
        print("Enhancing transcript with GPT...")
        enhanced_text = enhance_transcript_with_gpt(transcript_text)

        # استخراج القرارات والمهام
        print("Extracting decisions and tasks...")
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

        # إنشاء مقطع نصي واحد (مؤقتاً حتى يتم تفعيل diarization)
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
        print(f"Meeting {meeting.id} processing completed successfully.")

    except Exception as e:
        print(f"Error in normal processing: {str(e)}")
        raise
    finally:
        # تنظيف الملفات المؤقتة
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)