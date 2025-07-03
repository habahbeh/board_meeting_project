# speaker_identification/utils/diarization.py

import torch
import numpy as np
from pyannote.audio import Pipeline
from django.conf import settings
import os
import logging
from .voice_embeddings import (
    extract_voice_embedding,
    load_embedding_from_speaker,
    compare_embeddings,
    get_speaker_encoder
)
import torchaudio
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def perform_speaker_diarization(audio_file_path, num_speakers=None):
    """
    تقسيم الصوت حسب المتحدثين باستخدام pyannote.audio

    Args:
        audio_file_path: مسار الملف الصوتي
        num_speakers: عدد المتحدثين المتوقع (اختياري)

    Returns:
        list: قائمة من (speaker_label, start_time, end_time)
    """
    try:
        logger.info(f"Starting speaker diarization for: {audio_file_path}")

        # التحقق من وجود Hugging Face token
        hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")

        # تحميل pipeline
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        # إذا كان لدينا عدد المتحدثين، استخدمه
        if num_speakers:
            pipeline.instantiate({"num_speakers": num_speakers})

        # تشغيل diarization
        logger.info("Running diarization pipeline...")
        diarization = pipeline(audio_file_path)

        # تحويل النتائج إلى قائمة
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'speaker_label': speaker,
                'start': turn.start,
                'end': turn.end
            })
            logger.info(f"Found segment: {speaker} from {turn.start:.2f}s to {turn.end:.2f}s")

        logger.info(f"Found {len(segments)} segments from {len(set(s['speaker_label'] for s in segments))} speakers")
        return segments

    except Exception as e:
        logger.error(f"Error in speaker diarization: {str(e)}")
        # إرجاع تقسيم افتراضي في حالة الفشل
        return [{
            'speaker_label': 'SPEAKER_00',
            'start': 0,
            'end': 300  # 5 دقائق
        }]


def extract_segment_embedding(audio_file_path, start_time, end_time):
    """
    استخراج البصمة الصوتية من مقطع محدد من الملف الصوتي

    Args:
        audio_file_path: مسار الملف الصوتي
        start_time: وقت البداية بالثواني
        end_time: وقت النهاية بالثواني

    Returns:
        numpy array: البصمة الصوتية للمقطع
    """
    try:
        # استخدام pydub لقص المقطع
        audio = AudioSegment.from_file(audio_file_path)

        # تحويل الأوقات إلى ميلي ثانية
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)

        # قص المقطع
        segment = audio[start_ms:end_ms]

        # حفظ المقطع مؤقتاً
        temp_path = f"/tmp/segment_{start_time}_{end_time}.wav"
        segment.export(temp_path, format="wav")

        # استخراج البصمة الصوتية
        embedding = extract_voice_embedding(temp_path)

        # حذف الملف المؤقت
        os.remove(temp_path)

        return embedding

    except Exception as e:
        logger.error(f"Error extracting segment embedding: {str(e)}")
        return None


def identify_speakers_with_embeddings(audio_file_path, diarization_segments):
    """
    تحديد هوية المتحدثين باستخدام البصمات الصوتية

    Args:
        audio_file_path: مسار الملف الصوتي
        diarization_segments: نتائج diarization

    Returns:
        list: قائمة المقاطع مع هوية المتحدثين
    """
    from speaker_identification.models import Speaker

    logger.info("Starting speaker identification with voice embeddings...")

    # تحميل جميع المتحدثين الذين لديهم بصمات صوتية
    speakers_with_embeddings = []
    for speaker in Speaker.objects.all():
        embedding = load_embedding_from_speaker(speaker)
        if embedding is not None:
            speakers_with_embeddings.append({
                'speaker': speaker,
                'embedding': embedding
            })
            logger.info(f"Loaded embedding for: {speaker.name}")

    if not speakers_with_embeddings:
        logger.warning("No speakers with voice embeddings found!")
        return diarization_segments

    # معالجة كل مقطع
    identified_segments = []
    speaker_mapping = {}  # ربط التسميات مع المتحدثين الحقيقيين

    for segment in diarization_segments:
        speaker_label = segment['speaker_label']

        # إذا لم نحدد هذا المتحدث بعد
        if speaker_label not in speaker_mapping:
            logger.info(f"Identifying speaker: {speaker_label}")

            # استخراج بصمة صوتية من منتصف المقطع
            mid_time = (segment['start'] + segment['end']) / 2
            sample_start = max(segment['start'], mid_time - 2)  # عينة 4 ثوانٍ
            sample_end = min(segment['end'], mid_time + 2)

            segment_embedding = extract_segment_embedding(
                audio_file_path,
                sample_start,
                sample_end
            )

            if segment_embedding is not None:
                # مقارنة مع جميع المتحدثين المسجلين
                best_match = None
                best_score = 0.0

                for speaker_data in speakers_with_embeddings:
                    is_same, score = compare_embeddings(
                        segment_embedding,
                        speaker_data['embedding'],
                        threshold=0.6  # عتبة أقل للمرونة
                    )

                    logger.info(f"Comparing with {speaker_data['speaker'].name}: score={score:.3f}")

                    if score > best_score:
                        best_score = score
                        best_match = speaker_data['speaker']

                # إذا كان التطابق جيداً بما فيه الكفاية
                if best_score > 0.6:
                    speaker_mapping[speaker_label] = best_match
                    logger.info(f"Matched {speaker_label} to {best_match.name} (score: {best_score:.3f})")
                else:
                    logger.warning(f"No good match found for {speaker_label} (best score: {best_score:.3f})")
                    # إنشاء متحدث جديد
                    unknown_speaker = Speaker.objects.create(
                        name=f"متحدث غير معروف {speaker_label}",
                        position="غير محدد",
                        speaker_type="unknown"
                    )
                    speaker_mapping[speaker_label] = unknown_speaker

        # إضافة المقطع مع هوية المتحدث
        identified_segment = segment.copy()
        identified_segment['speaker'] = speaker_mapping.get(
            speaker_label,
            Speaker.objects.get_or_create(
                name=f"متحدث {speaker_label}",
                defaults={'position': 'غير محدد', 'speaker_type': 'unknown'}
            )[0]
        )
        identified_segments.append(identified_segment)

    logger.info(f"Identified {len(speaker_mapping)} unique speakers")
    return identified_segments


def process_meeting_with_speaker_recognition(audio_file_path):
    """
    معالجة اجتماع كامل مع التعرف على المتحدثين

    Args:
        audio_file_path: مسار الملف الصوتي للاجتماع

    Returns:
        list: قائمة المقاطع مع هوية المتحدثين
    """
    try:
        # الخطوة 1: Speaker Diarization
        logger.info("Step 1: Speaker Diarization")
        diarization_segments = perform_speaker_diarization(audio_file_path)

        # الخطوة 2: التعرف على المتحدثين
        logger.info("Step 2: Speaker Identification")
        identified_segments = identify_speakers_with_embeddings(
            audio_file_path,
            diarization_segments
        )

        return identified_segments

    except Exception as e:
        logger.error(f"Error in meeting processing: {str(e)}")
        raise


# دالة اختبار
def test_speaker_recognition():
    """اختبار نظام التعرف على المتحدثين"""
    from speaker_identification.models import Speaker

    # البحث عن ملف اجتماع للاختبار
    if os.path.exists("media/meeting_audio"):
        audio_files = [f for f in os.listdir("media/meeting_audio") if f.endswith('.mp3')]
        if audio_files:
            test_file = os.path.join("media/meeting_audio", audio_files[0])
            logger.info(f"Testing with: {test_file}")

            # تشغيل المعالجة
            segments = process_meeting_with_speaker_recognition(test_file)

            # طباعة النتائج
            for seg in segments[:5]:  # أول 5 مقاطع
                logger.info(f"{seg['speaker'].name}: {seg['start']:.2f}s - {seg['end']:.2f}s")

            return True

    logger.warning("No test audio file found")
    return False