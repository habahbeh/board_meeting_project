# speaker_identification/utils/voice_comparison.py

import os
import torch
import numpy as np
from pyannote.audio import Model, Inference
from pyannote.audio.pipelines import SpeakerDiarization
from pyannote.core import Segment
from scipy.spatial.distance import cosine
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# تحميل النماذج
embedding_model = None
diarization_pipeline = None


def get_embedding_model():
    """تحميل نموذج استخراج البصمات الصوتية"""
    global embedding_model
    if embedding_model is None:
        logger.info("Loading embedding model...")
        # نموذج استخراج البصمات الصوتية
        embedding_model = Model.from_pretrained(
            "pyannote/embedding",
            use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
        )
        embedding_model = Inference(embedding_model, window="whole")
    return embedding_model


def get_diarization_pipeline():
    """تحميل pipeline للـ diarization"""
    global diarization_pipeline
    if diarization_pipeline is None:
        logger.info("Loading diarization pipeline...")
        diarization_pipeline = SpeakerDiarization.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
        )
    return diarization_pipeline


def extract_speaker_embedding(audio_file_path):
    """
    استخراج البصمة الصوتية من ملف صوتي

    Returns:
        numpy array: البصمة الصوتية (embedding)
    """
    try:
        logger.info(f"Extracting embedding from: {audio_file_path}")

        # الحصول على نموذج الـ embedding
        inference = get_embedding_model()

        # استخراج البصمة الصوتية من الملف كاملاً
        embedding = inference(audio_file_path)

        # تحويل إلى numpy array
        if isinstance(embedding, torch.Tensor):
            embedding = embedding.numpy()

        logger.info(f"Extracted embedding shape: {embedding.shape}")
        return embedding

    except Exception as e:
        logger.error(f"Error extracting embedding: {str(e)}")
        return None


def compare_embeddings(embedding1, embedding2):
    """
    مقارنة بصمتين صوتيتين

    Returns:
        float: نسبة التشابه (0-1)
    """
    try:
        # التأكد من أن البصمات numpy arrays
        if isinstance(embedding1, torch.Tensor):
            embedding1 = embedding1.numpy()
        if isinstance(embedding2, torch.Tensor):
            embedding2 = embedding2.numpy()

        # حساب التشابه (1 - cosine distance)
        similarity = 1 - cosine(embedding1.flatten(), embedding2.flatten())

        return float(similarity)

    except Exception as e:
        logger.error(f"Error comparing embeddings: {str(e)}")
        return 0.0


def save_speaker_embedding(speaker):
    """حفظ البصمة الصوتية للمتحدث"""
    if not speaker.reference_audio:
        logger.warning(f"Speaker {speaker.name} has no reference audio")
        return False

    try:
        # استخراج البصمة
        embedding = extract_speaker_embedding(speaker.reference_audio.path)

        if embedding is not None:
            # حفظ البصمة في قاعدة البيانات
            import pickle
            speaker.voice_embedding = pickle.dumps(embedding)
            speaker.save()
            logger.info(f"Saved embedding for speaker: {speaker.name}")
            return True

    except Exception as e:
        logger.error(f"Error saving embedding for {speaker.name}: {str(e)}")

    return False


def load_speaker_embedding(speaker):
    """تحميل البصمة الصوتية للمتحدث"""
    if speaker.voice_embedding:
        try:
            import pickle
            embedding = pickle.loads(speaker.voice_embedding)
            return embedding
        except:
            pass

    # إذا لم تكن محفوظة، استخرجها
    if speaker.reference_audio:
        embedding = extract_speaker_embedding(speaker.reference_audio.path)
        if embedding is not None:
            save_speaker_embedding(speaker)
        return embedding

    return None


def identify_speaker_from_segment(audio_file_path, start_time, end_time):
    """
    تحديد المتحدث من مقطع صوتي

    Args:
        audio_file_path: مسار الملف الصوتي
        start_time: وقت البداية
        end_time: وقت النهاية

    Returns:
        Speaker object or None
    """
    from speaker_identification.models import Speaker

    try:
        # استخراج البصمة الصوتية للمقطع
        inference = get_embedding_model()
        segment = Segment(start_time, end_time)
        segment_embedding = inference.crop(audio_file_path, segment)

        # مقارنة مع جميع المتحدثين
        best_speaker = None
        best_score = 0.0
        threshold = 0.7  # عتبة التشابه

        for speaker in Speaker.objects.all():
            speaker_embedding = load_speaker_embedding(speaker)
            if speaker_embedding is not None:
                similarity = compare_embeddings(segment_embedding, speaker_embedding)
                logger.info(f"Comparing with {speaker.name}: {similarity:.3f}")

                if similarity > best_score and similarity > threshold:
                    best_score = similarity
                    best_speaker = speaker

        if best_speaker:
            logger.info(f"Identified speaker: {best_speaker.name} (score: {best_score:.3f})")
        else:
            logger.warning(f"No speaker identified (best score: {best_score:.3f})")

        return best_speaker, best_score

    except Exception as e:
        logger.error(f"Error identifying speaker: {str(e)}")
        return None, 0.0


def process_meeting_with_diarization(audio_file_path):
    """
    معالجة اجتماع كامل مع diarization وتحديد المتحدثين

    Returns:
        list of dict: قائمة المقاطع مع المتحدثين المحددين
    """
    logger.info(f"Starting diarization for: {audio_file_path}")

    try:
        # 1. تشغيل diarization
        pipeline = get_diarization_pipeline()
        diarization = pipeline(audio_file_path)

        # 2. معالجة كل مقطع
        segments = []
        speaker_mapping = {}  # ربط labels مع المتحدثين الحقيقيين

        for turn, _, speaker_label in diarization.itertracks(yield_label=True):
            start_time = turn.start
            end_time = turn.end

            # تحديد المتحدث إذا لم يتم تحديده بعد
            if speaker_label not in speaker_mapping:
                logger.info(f"Identifying speaker for label: {speaker_label}")

                # تحديد المتحدث من البصمة الصوتية
                speaker, score = identify_speaker_from_segment(
                    audio_file_path,
                    start_time,
                    end_time
                )

                if speaker:
                    speaker_mapping[speaker_label] = speaker
                    logger.info(f"Mapped {speaker_label} to {speaker.name}")
                else:
                    # إنشاء متحدث جديد
                    from speaker_identification.models import Speaker
                    new_speaker = Speaker.objects.create(
                        name=f"متحدث {speaker_label}",
                        position="غير محدد",
                        speaker_type="unknown"
                    )
                    speaker_mapping[speaker_label] = new_speaker

            segments.append({
                'speaker': speaker_mapping[speaker_label],
                'start': start_time,
                'end': end_time,
                'label': speaker_label
            })

        logger.info(f"Found {len(segments)} segments with {len(speaker_mapping)} speakers")
        return segments

    except Exception as e:
        logger.error(f"Error in diarization: {str(e)}")
        return []


# دالة اختبار
def test_voice_comparison():
    """اختبار النظام"""
    from speaker_identification.models import Speaker

    print("🔧 Testing Voice Comparison System")
    print("=" * 50)

    # 1. اختبار استخراج البصمات
    print("\n1. Testing embedding extraction...")
    test_speaker = Speaker.objects.filter(reference_audio__isnull=False).first()

    if test_speaker:
        embedding = extract_speaker_embedding(test_speaker.reference_audio.path)
        if embedding is not None:
            print(f"✅ Extracted embedding for {test_speaker.name}")
            print(f"   Shape: {embedding.shape}")

            # حفظ البصمة
            save_speaker_embedding(test_speaker)
            print(f"✅ Saved embedding to database")
        else:
            print("❌ Failed to extract embedding")
    else:
        print("❌ No speakers with audio found")

    # 2. اختبار المقارنة
    print("\n2. Testing embedding comparison...")
    speakers = list(Speaker.objects.filter(reference_audio__isnull=False)[:2])

    if len(speakers) >= 2:
        emb1 = load_speaker_embedding(speakers[0])
        emb2 = load_speaker_embedding(speakers[1])

        if emb1 is not None and emb2 is not None:
            similarity = compare_embeddings(emb1, emb2)
            print(f"✅ Similarity between {speakers[0].name} and {speakers[1].name}: {similarity:.3f}")

            # مقارنة مع نفسه
            self_similarity = compare_embeddings(emb1, emb1)
            print(f"✅ Self-similarity for {speakers[0].name}: {self_similarity:.3f}")
        else:
            print("❌ Failed to load embeddings")

    print("\n✅ Test completed!")


if __name__ == "__main__":
    test_voice_comparison()