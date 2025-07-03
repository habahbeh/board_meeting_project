# process_with_voice.py - معالج رئيسي مع مقارنة صوتية

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'board_meeting_project.settings')
django.setup()

from django.conf import settings
from transcription.models import Meeting, TranscriptSegment, MeetingReport
from speaker_identification.models import Speaker
from speaker_identification.utils.voice_comparison import (
    process_meeting_with_diarization,
    save_speaker_embedding,
    get_embedding_model,
    get_diarization_pipeline
)
import openai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تكوين OpenAI
openai.api_key = settings.OPENAI_API_KEY


def prepare_speakers():
    """تحضير البصمات الصوتية للمتحدثين"""
    print("\n🎤 Preparing speaker embeddings...")

    speakers = Speaker.objects.filter(reference_audio__isnull=False)
    prepared = 0

    for speaker in speakers:
        if not speaker.voice_embedding:
            print(f"  Processing {speaker.name}...")
            if save_speaker_embedding(speaker):
                prepared += 1
                print(f"  ✅ {speaker.name} ready")
            else:
                print(f"  ❌ Failed for {speaker.name}")
        else:
            print(f"  ✓ {speaker.name} already has embedding")

    print(f"\n✅ Prepared {prepared} new embeddings")
    return speakers.count()


def process_meeting_auto(meeting_id):
    """معالجة اجتماع مع مقارنة صوتية تلقائية"""
    meeting = Meeting.objects.get(id=meeting_id)

    print(f"\n🎯 Processing meeting: {meeting.title}")
    print(f"📁 Audio file: {meeting.audio_file.name}")

    try:
        # 1. تحضير المتحدثين
        speaker_count = prepare_speakers()
        if speaker_count == 0:
            print("⚠️ Warning: No speakers with reference audio found!")

        # 2. تحميل النماذج
        print("\n📊 Loading AI models...")
        get_embedding_model()
        get_diarization_pipeline()
        print("✅ Models loaded")

        # 3. معالجة الصوت مع diarization
        audio_path = meeting.audio_file.path
        print(f"\n🔊 Processing audio with speaker diarization...")

        segments = process_meeting_with_diarization(audio_path)

        if not segments:
            print("❌ No segments found!")
            return

        print(f"✅ Found {len(segments)} segments")

        # 4. نسخ الصوت بـ Whisper
        print(f"\n📝 Transcribing with Whisper...")
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ar"
            )

        print(f"✅ Transcribed {len(transcript)} characters")

        # 5. دمج النص مع المقاطع
        print(f"\n🔗 Merging transcription with speaker segments...")

        # تقسيم النص إلى جمل
        sentences = [s.strip() + '.' for s in transcript.split('.') if s.strip()]

        # توزيع الجمل على المقاطع الصوتية
        merged_segments = []
        sentence_idx = 0
        sentences_per_segment = max(1, len(sentences) // len(segments))

        for seg in segments:
            segment_text = ""

            # جمع الجمل لهذا المقطع
            for _ in range(sentences_per_segment):
                if sentence_idx < len(sentences):
                    segment_text += sentences[sentence_idx] + " "
                    sentence_idx += 1

            if segment_text.strip():
                merged_segments.append({
                    'speaker': seg['speaker'],
                    'text': segment_text.strip(),
                    'start': seg['start'],
                    'end': seg['end']
                })

        # إضافة الجمل المتبقية للمقطع الأخير
        while sentence_idx < len(sentences):
            if merged_segments:
                merged_segments[-1]['text'] += " " + sentences[sentence_idx]
            sentence_idx += 1

        # 6. حذف المقاطع القديمة
        TranscriptSegment.objects.filter(meeting=meeting).delete()

        # 7. حفظ المقاطع الجديدة
        print(f"\n💾 Saving segments to database...")

        decisions = []
        tasks = []

        for seg in merged_segments:
            # تحديد نوع المقطع
            is_decision = any(word in seg['text'] for word in ['القرار', 'نقرر', 'الموافقة', 'تقرر'])
            is_task = any(word in seg['text'] for word in ['مهمة', 'نكلف', 'يجب على', 'تكليف'])

            if is_decision:
                decisions.append(f"{seg['speaker'].name}: {seg['text']}")
            if is_task:
                tasks.append(f"{seg['speaker'].name}: {seg['text']}")

            TranscriptSegment.objects.create(
                meeting=meeting,
                speaker=seg['speaker'],
                text=seg['text'],
                start_time=seg['start'],
                end_time=seg['end'],
                confidence=0.85,
                is_decision=is_decision,
                is_action_item=is_task
            )

        print(f"✅ Saved {len(merged_segments)} segments")

        # 8. إنشاء التقرير
        print(f"\n📋 Creating meeting report...")

        # إحصائيات المتحدثين
        speaker_stats = {}
        for seg in merged_segments:
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
إجمالي المقاطع: {len(merged_segments)}

المتحدثون (حسب المقارنة الصوتية):
"""
        for name, stats in speaker_stats.items():
            duration_min = stats['duration'] / 60
            summary += f"\n- {name}: {stats['count']} مداخلة ({duration_min:.1f} دقيقة)"

        # حفظ التقرير
        MeetingReport.objects.filter(meeting=meeting).delete()
        MeetingReport.objects.create(
            meeting=meeting,
            summary=summary.strip(),
            decisions="\n".join(decisions) or "لا توجد قرارات",
            action_items="\n".join(tasks) or "لا توجد مهام"
        )

        # 9. تحديث حالة الاجتماع
        meeting.processed = True
        meeting.save()

        print(f"\n✅ Meeting processed successfully!")
        print(f"📊 Summary:")
        print(f"   - Speakers identified: {len(speaker_stats)}")
        print(f"   - Total segments: {len(merged_segments)}")
        print(f"   - Decisions: {len(decisions)}")
        print(f"   - Tasks: {len(tasks)}")

        # 10. عرض عينة من النتائج
        print(f"\n📝 Sample results:")
        print("-" * 60)

        for seg in TranscriptSegment.objects.filter(meeting=meeting)[:5]:
            print(f"\n🎤 {seg.speaker.name} ({seg.start_time:.1f}s - {seg.end_time:.1f}s):")
            print(f"   \"{seg.text[:100]}...\"")
            if seg.is_decision:
                print("   ⚡ [قرار]")
            if seg.is_action_item:
                print("   📌 [مهمة]")

        return True

    except Exception as e:
        logger.error(f"Error processing meeting: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# تشغيل المعالجة
if __name__ == "__main__":
    import sys

    # تحقق من Hugging Face token
    if not os.getenv("HUGGINGFACE_TOKEN"):
        print("❌ Error: HUGGINGFACE_TOKEN not found in environment!")
        print("Please add it to .env file")
        sys.exit(1)

    # معالجة اجتماع
    if len(sys.argv) > 1:
        meeting_id = int(sys.argv[1])
        meeting = Meeting.objects.get(id=meeting_id)
    else:
        meeting = Meeting.objects.filter(processed=False).first()
        if not meeting:
            meeting = Meeting.objects.last()

    if meeting:
        print(f"\n🚀 Starting automatic voice comparison processing...")
        print("=" * 60)

        # إعادة تعيين الحالة
        meeting.processed = False
        meeting.save()

        # معالجة
        success = process_meeting_auto(meeting.id)

        if success:
            print("\n🎉 Success! Check the results in the web interface.")
        else:
            print("\n😞 Processing failed. Check the logs.")
    else:
        print("❌ No meetings found!")
        print("Upload a meeting first.")