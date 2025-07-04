# audio_processing/tasks_enhanced.py - نسخة محسنة مع المقارنة الصوتية

import os
import tempfile
import time
from django.conf import settings
from django.utils.translation import gettext as _
from transcription.models import Meeting, TranscriptSegment, MeetingReport
from speaker_identification.models import Speaker
from audio_processing.utils.preprocessing import convert_audio_to_wav, enhance_audio_quality
from transcription.utils.whisper_gpt4o import transcribe_with_whisper
import logging
import openai

logger = logging.getLogger(__name__)

# تكوين OpenAI
if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
    openai.api_key = settings.OPENAI_API_KEY


def process_meeting_task(meeting_id):
    """معالجة الاجتماع - نقطة الدخول الرئيسية"""
    meeting = Meeting.objects.get(id=meeting_id)

    try:
        # التحقق من الإعدادات
        use_voice_comparison = getattr(settings, 'USE_VOICE_COMPARISON', False)

        # التحقق من توفر المتطلبات للمقارنة الصوتية
        if use_voice_comparison and os.getenv("HUGGINGFACE_TOKEN"):
            logger.info(f"Processing meeting {meeting_id} with voice comparison")
            process_meeting_with_voice_comparison(meeting)
        elif settings.OPENAI_API_KEY and not getattr(settings, 'TESTING_MODE', False):
            logger.info(f"Processing meeting {meeting_id} with OpenAI")
            process_meeting_with_openai(meeting)
        else:
            logger.info(f"Processing meeting {meeting_id} in test mode")
            process_meeting_test_mode(meeting)

    except Exception as e:
        logger.error(f"Error processing meeting {meeting_id}: {str(e)}")
        meeting.processed = False
        meeting.save()
        raise e


def process_meeting_with_voice_comparison(meeting):
    """معالجة مع المقارنة الصوتية"""
    print(f"🎤 Voice Comparison Processing for meeting {meeting.id}")

    try:
        # استيراد وظائف المقارنة الصوتية
        from speaker_identification.utils.voice_comparison import (
            process_meeting_with_diarization,
            save_speaker_embedding
        )

        # 1. تحضير البصمات الصوتية للمتحدثين
        prepare_speaker_embeddings()

        # 2. معالجة الصوت مع diarization
        audio_path = meeting.audio_file.path
        segments = process_meeting_with_diarization(audio_path)

        if not segments:
            raise Exception("No segments found from diarization")

        print(f"✅ Found {len(segments)} segments")

        # 3. نسخ الصوت بـ Whisper
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ar"
            )

        # 4. دمج النص مع مقاطع المتحدثين
        merged_segments = merge_transcript_with_diarization(
            transcript['text'],
            segments
        )

        # 5. حفظ النتائج
        save_segments_to_database(meeting, merged_segments)

        # 6. إنشاء التقرير
        create_meeting_report_from_segments(meeting, merged_segments)

        # 7. تحديث حالة الاجتماع
        meeting.processed = True
        meeting.save()

        print(f"✅ Meeting {meeting.id} processed successfully with voice comparison!")

    except ImportError as e:
        logger.error(f"Voice comparison modules not available: {str(e)}")
        logger.info("Falling back to OpenAI processing")
        process_meeting_with_openai(meeting)
    except Exception as e:
        logger.error(f"Voice comparison error: {str(e)}")
        logger.info("Falling back to OpenAI processing")
        process_meeting_with_openai(meeting)


def process_meeting_with_openai(meeting):
    """معالجة حقيقية باستخدام OpenAI"""
    print(f"Starting OpenAI processing for meeting {meeting.id}")

    temp_dir = tempfile.mkdtemp()

    try:
        # 1. تحضير الملف الصوتي
        audio_path = os.path.join(settings.MEDIA_ROOT, str(meeting.audio_file))
        print(f"Audio file: {audio_path}")

        # 2. نسخ الصوت باستخدام Whisper
        print("Transcribing with Whisper...")
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ar",
                response_format="text"
            )

        print(f"Transcription complete. Length: {len(transcript)} characters")

        # 3. تحليل النص وتحديد المتحدثين باستخدام GPT
        print("Analyzing transcript with GPT...")

        # تقسيم النص إلى أجزاء صغيرة للمعالجة
        segments = split_text_into_segments(transcript)
        print(f"Split into {len(segments)} segments")

        # جلب المتحدثين المحتملين
        speakers = Speaker.objects.all()
        speaker_info = "\n".join([f"- {s.name} ({s.position})" for s in speakers])

        # معالجة كل مقطع
        processed_segments = []
        current_speaker = None

        for i, segment_text in enumerate(segments):
            print(f"Processing segment {i + 1}/{len(segments)}")

            # استخدام GPT لتحديد المتحدث
            prompt = f"""
            لديك هذه القائمة من المتحدثين المحتملين:
            {speaker_info}

            النص التالي من اجتماع. حدد من المتحدث:
            "{segment_text}"

            ابحث عن:
            1. عبارات تعريف (أنا فلان، معكم فلان)
            2. ذكر الأسماء (شكراً دكتور أحمد)
            3. تغيير المتحدث (أعطي الكلمة لـ)

            أجب فقط باسم المتحدث أو "غير محدد" إذا لم تستطع التحديد.
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "أنت خبير في تحليل محاضر الاجتماعات"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.3
                )

                speaker_name = response.choices[0].message.content.strip()
                print(f"GPT identified speaker: {speaker_name}")

                # البحث عن المتحدث في قاعدة البيانات
                speaker_obj = None
                for s in speakers:
                    if s.name in speaker_name or speaker_name in s.name:
                        speaker_obj = s
                        current_speaker = s
                        break

                if not speaker_obj:
                    if current_speaker:
                        speaker_obj = current_speaker
                    else:
                        speaker_obj = Speaker.objects.get_or_create(
                            name="متحدث غير محدد",
                            defaults={'position': 'غير محدد', 'speaker_type': 'unknown'}
                        )[0]

            except Exception as e:
                print(f"GPT error: {e}")
                speaker_obj = current_speaker or Speaker.objects.get_or_create(
                    name="متحدث غير محدد",
                    defaults={'position': 'غير محدد', 'speaker_type': 'unknown'}
                )[0]

            # تحديد نوع المقطع
            is_decision = any(word in segment_text for word in ['القرار', 'نقرر', 'الموافقة على', 'تقرر'])
            is_task = any(word in segment_text for word in ['مهمة', 'نكلف', 'يجب على', 'تكليف'])

            processed_segments.append({
                'speaker': speaker_obj,
                'text': segment_text,
                'is_decision': is_decision,
                'is_task': is_task,
                'start_time': i * 30,  # تقدير الوقت
                'end_time': (i + 1) * 30
            })

        # 4. حفظ المقاطع في قاعدة البيانات
        print("Saving segments to database...")
        for seg in processed_segments:
            TranscriptSegment.objects.create(
                meeting=meeting,
                speaker=seg['speaker'],
                text=seg['text'],
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                confidence=0.85,
                is_decision=seg['is_decision'],
                is_action_item=seg['is_task']
            )

        # 5. إنشاء التقرير
        print("Creating meeting report...")
        create_meeting_report(meeting, processed_segments)

        # 6. تحديث حالة المعالجة
        meeting.processed = True
        meeting.save()
        print(f"Meeting {meeting.id} processed successfully!")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def process_meeting_test_mode(meeting):
    """وضع تجريبي مع بيانات واضحة"""
    print(f"Test mode for meeting {meeting.id}")

    # بيانات تجريبية واضحة
    test_data = [
        ("د. أحمد محمد", "السلام عليكم، أنا الدكتور أحمد محمد رئيس مجلس الإدارة. نبدأ اجتماعنا اليوم.", False, False),
        ("د. أحمد محمد", "جدول أعمالنا يتضمن مناقشة النتائج المالية وخطط التوسع.", False, False),
        ("أ. سارة خالد", "شكراً دكتور أحمد. أنا سارة خالد المدير المالي. النتائج المالية ممتازة هذا الربع.", False,
         False),
        ("أ. سارة خالد", "حققنا نمواً بنسبة 15% مقارنة بالربع السابق.", False, False),
        ("م. فاطمة علي", "أنا فاطمة علي المدير التنفيذي. أقترح زيادة الاستثمار في التسويق.", False, False),
        ("د. أحمد محمد", "القرار الأول: الموافقة على زيادة ميزانية التسويق بنسبة 10%.", True, False),
        ("د. أحمد محمد", "مهمة لسارة: إعداد خطة تفصيلية للميزانية الجديدة خلال أسبوع.", False, True),
        ("أ. سارة خالد", "تم استلام المهمة وسأنفذها في الموعد المحدد.", False, False),
    ]

    # إنشاء المتحدثين
    speakers = {}
    speakers_data = [
        ("د. أحمد محمد", "رئيس مجلس الإدارة", "board"),
        ("أ. سارة خالد", "المدير المالي", "executive"),
        ("م. فاطمة علي", "المدير التنفيذي", "executive"),
    ]

    for name, position, type_ in speakers_data:
        speaker, _ = Speaker.objects.get_or_create(
            name=name,
            defaults={'position': position, 'speaker_type': type_}
        )
        speakers[name] = speaker

    # إنشاء المقاطع
    start_time = 0
    for speaker_name, text, is_decision, is_task in test_data:
        TranscriptSegment.objects.create(
            meeting=meeting,
            speaker=speakers[speaker_name],
            text=text,
            start_time=start_time,
            end_time=start_time + 20,
            confidence=0.95,
            is_decision=is_decision,
            is_action_item=is_task
        )
        start_time += 20

    # إنشاء التقرير
    summary = """
    اجتماع تجريبي لعرض النظام
    المشاركون: د. أحمد محمد، أ. سارة خالد، م. فاطمة علي
    """

    MeetingReport.objects.create(
        meeting=meeting,
        summary=summary,
        decisions="1. الموافقة على زيادة ميزانية التسويق بنسبة 10%",
        action_items="1. سارة خالد: إعداد خطة تفصيلية للميزانية الجديدة خلال أسبوع"
    )

    meeting.processed = True
    meeting.save()
    print("Test meeting processed successfully!")


def split_text_into_segments(text, segment_size=200):
    """تقسيم النص إلى مقاطع صغيرة"""
    sentences = text.split('.')
    segments = []
    current_segment = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        # إذا كان المقطع الحالي صغيراً، أضف الجملة
        if len(current_segment) < segment_size:
            current_segment += sentence + "."
        else:
            # احفظ المقطع الحالي وابدأ مقطع جديد
            if current_segment:
                segments.append(current_segment.strip())
            current_segment = sentence + "."

    # أضف المقطع الأخير
    if current_segment:
        segments.append(current_segment.strip())

    return segments


def create_meeting_report(meeting, segments):
    """إنشاء تقرير الاجتماع"""
    # إحصائيات المتحدثين
    speakers_stats = {}
    for seg in segments:
        speaker_name = seg['speaker'].name
        if speaker_name not in speakers_stats:
            speakers_stats[speaker_name] = 0
        speakers_stats[speaker_name] += 1

    # الملخص
    summary = f"""
    اجتماع بتاريخ {meeting.date}
    عدد المشاركين: {len(speakers_stats)}
    إجمالي المقاطع: {len(segments)}

    المشاركون:
    """

    for speaker, count in speakers_stats.items():
        summary += f"\n- {speaker} ({count} مداخلة)"

    # القرارات
    decisions = [seg for seg in segments if seg['is_decision']]
    decisions_text = ""
    for i, dec in enumerate(decisions, 1):
        decisions_text += f"{i}. {dec['speaker'].name}: {dec['text']}\n"

    # المهام
    tasks = [seg for seg in segments if seg['is_task']]
    tasks_text = ""
    for i, task in enumerate(tasks, 1):
        tasks_text += f"{i}. {task['speaker'].name}: {task['text']}\n"

    MeetingReport.objects.create(
        meeting=meeting,
        summary=summary.strip(),
        decisions=decisions_text.strip() or "لا توجد قرارات",
        action_items=tasks_text.strip() or "لا توجد مهام"
    )


def prepare_speaker_embeddings():
    """تحضير البصمات الصوتية للمتحدثين"""
    try:
        from speaker_identification.utils.voice_comparison import save_speaker_embedding

        speakers = Speaker.objects.filter(reference_audio__isnull=False)

        for speaker in speakers:
            if not speaker.voice_embedding:
                try:
                    save_speaker_embedding(speaker)
                    logger.info(f"Prepared embedding for {speaker.name}")
                except Exception as e:
                    logger.warning(f"Failed to prepare embedding for {speaker.name}: {e}")
    except ImportError:
        logger.warning("Voice comparison module not available")


def merge_transcript_with_diarization(transcript_text, diarization_segments):
    """دمج النص المنسوخ مع مقاطع diarization"""

    # تقسيم النص إلى جمل
    sentences = [s.strip() + '.' for s in transcript_text.split('.') if s.strip()]

    # توزيع الجمل على المقاطع
    merged = []
    sentence_idx = 0

    for segment in diarization_segments:
        segment_duration = segment['end'] - segment['start']
        segment_text = ""

        # تقدير عدد الجمل لهذا المقطع
        while sentence_idx < len(sentences) and len(segment_text) < segment_duration * 20:
            segment_text += sentences[sentence_idx] + " "
            sentence_idx += 1

        if segment_text.strip():
            # تحديد نوع المقطع
            is_decision = any(word in segment_text for word in ['القرار', 'نقرر', 'الموافقة'])
            is_task = any(word in segment_text for word in ['مهمة', 'نكلف', 'يجب على'])

            merged.append({
                'speaker': segment['speaker'],
                'text': segment_text.strip(),
                'start': segment['start'],
                'end': segment['end'],
                'is_decision': is_decision,
                'is_task': is_task
            })

    return merged


def save_segments_to_database(meeting, segments):
    """حفظ المقاطع في قاعدة البيانات"""
    # حذف المقاطع القديمة
    TranscriptSegment.objects.filter(meeting=meeting).delete()

    # إنشاء المقاطع الجديدة
    for seg in segments:
        TranscriptSegment.objects.create(
            meeting=meeting,
            speaker=seg['speaker'],
            text=seg['text'],
            start_time=seg['start'],
            end_time=seg['end'],
            confidence=0.85,
            is_decision=seg.get('is_decision', False),
            is_action_item=seg.get('is_task', False)
        )


def create_meeting_report_from_segments(meeting, segments):
    """إنشاء تقرير من المقاطع المدمجة"""
    # إحصائيات المتحدثين
    speaker_stats = {}
    for seg in segments:
        name = seg['speaker'].name
        if name not in speaker_stats:
            speaker_stats[name] = {
                'count': 0,
                'duration': 0
            }
        speaker_stats[name]['count'] += 1
        speaker_stats[name]['duration'] += seg['end'] - seg['start']

    summary = f"""
اجتماع: {meeting.title}
التاريخ: {meeting.date}
عدد المتحدثين: {len(speaker_stats)}
إجمالي المقاطع: {len(segments)}

المتحدثون (حسب المقارنة الصوتية):
"""
    for name, stats in speaker_stats.items():
        duration_min = stats['duration'] / 60
        summary += f"\n- {name}: {stats['count']} مداخلة ({duration_min:.1f} دقيقة)"

    # القرارات والمهام
    decisions = []
    tasks = []

    for seg in segments:
        if seg.get('is_decision'):
            decisions.append(f"{seg['speaker'].name}: {seg['text']}")
        if seg.get('is_task'):
            tasks.append(f"{seg['speaker'].name}: {seg['text']}")

    # حفظ التقرير
    MeetingReport.objects.filter(meeting=meeting).delete()
    MeetingReport.objects.create(
        meeting=meeting,
        summary=summary.strip(),
        decisions="\n".join(decisions) or "لا توجد قرارات",
        action_items="\n".join(tasks) or "لا توجد مهام"
    )