# speaker_identification/utils/voice_embeddings.py

import os
import torch
import torchaudio
import numpy as np
from speechbrain.pretrained import EncoderClassifier
from django.conf import settings
import pickle
import logging

logger = logging.getLogger(__name__)

# تحميل نموذج استخراج البصمات الصوتية
speaker_encoder = None


def get_speaker_encoder():
    """الحصول على نموذج التشفير الصوتي"""
    global speaker_encoder
    if speaker_encoder is None:
        logger.info("Loading speaker encoder model...")
        speaker_encoder = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="models/speaker_encoder"
        )
    return speaker_encoder


def extract_voice_embedding(audio_file_path):
    """
    استخراج البصمة الصوتية من ملف صوتي

    Args:
        audio_file_path: مسار الملف الصوتي

    Returns:
        numpy array: البصمة الصوتية (embedding vector)
    """
    try:
        logger.info(f"Extracting voice embedding from: {audio_file_path}")

        # تحميل الملف الصوتي
        signal, fs = torchaudio.load(audio_file_path)

        # تحويل إلى mono إذا كان stereo
        if signal.shape[0] > 1:
            signal = torch.mean(signal, dim=0, keepdim=True)

        # إعادة العينات إلى 16kHz إذا لزم الأمر
        if fs != 16000:
            resampler = torchaudio.transforms.Resample(fs, 16000)
            signal = resampler(signal)

        # استخراج البصمة الصوتية
        encoder = get_speaker_encoder()
        embeddings = encoder.encode_batch(signal)

        # تحويل إلى numpy array
        embedding = embeddings.squeeze().cpu().numpy()

        logger.info(f"Extracted embedding shape: {embedding.shape}")
        return embedding

    except Exception as e:
        logger.error(f"Error extracting voice embedding: {str(e)}")
        raise


def save_embedding_to_speaker(speaker, embedding):
    """
    حفظ البصمة الصوتية في نموذج المتحدث

    Args:
        speaker: كائن Speaker
        embedding: numpy array للبصمة الصوتية
    """
    try:
        # تحويل إلى bytes للحفظ في قاعدة البيانات
        embedding_bytes = pickle.dumps(embedding)
        speaker.voice_embedding = embedding_bytes
        speaker.save()
        logger.info(f"Saved voice embedding for speaker: {speaker.name}")

    except Exception as e:
        logger.error(f"Error saving embedding: {str(e)}")
        raise


def load_embedding_from_speaker(speaker):
    """
    تحميل البصمة الصوتية من نموذج المتحدث

    Args:
        speaker: كائن Speaker

    Returns:
        numpy array: البصمة الصوتية أو None
    """
    try:
        if speaker.voice_embedding:
            embedding = pickle.loads(speaker.voice_embedding)
            return embedding
        return None

    except Exception as e:
        logger.error(f"Error loading embedding: {str(e)}")
        return None


def compare_embeddings(embedding1, embedding2, threshold=0.7):
    """
    مقارنة بصمتين صوتيتين

    Args:
        embedding1: البصمة الأولى
        embedding2: البصمة الثانية
        threshold: عتبة التشابه (0-1)

    Returns:
        tuple: (is_same_speaker, similarity_score)
    """
    try:
        # حساب cosine similarity
        from numpy.linalg import norm

        similarity = np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2))
        is_same = similarity > threshold

        return is_same, float(similarity)

    except Exception as e:
        logger.error(f"Error comparing embeddings: {str(e)}")
        return False, 0.0


def process_all_speaker_embeddings():
    """
    معالجة جميع المتحدثين الذين لديهم ملفات صوتية مرجعية
    """
    from speaker_identification.models import Speaker

    speakers_with_audio = Speaker.objects.filter(
        reference_audio__isnull=False,
        voice_embedding__isnull=True
    )

    processed = 0
    for speaker in speakers_with_audio:
        try:
            if speaker.reference_audio:
                audio_path = speaker.reference_audio.path
                if os.path.exists(audio_path):
                    embedding = extract_voice_embedding(audio_path)
                    save_embedding_to_speaker(speaker, embedding)
                    processed += 1
                    logger.info(f"Processed speaker: {speaker.name}")
                else:
                    logger.warning(f"Audio file not found for speaker: {speaker.name}")
        except Exception as e:
            logger.error(f"Error processing speaker {speaker.name}: {str(e)}")
            continue

    logger.info(f"Processed {processed} speakers")
    return processed


# دالة اختبار
def test_voice_embedding():
    """اختبار استخراج البصمة الصوتية"""
    from speaker_identification.models import Speaker

    # البحث عن متحدث لديه ملف صوتي
    speaker = Speaker.objects.filter(reference_audio__isnull=False).first()

    if speaker:
        logger.info(f"Testing with speaker: {speaker.name}")

        # استخراج البصمة
        embedding = extract_voice_embedding(speaker.reference_audio.path)
        logger.info(f"Embedding shape: {embedding.shape}")

        # حفظها
        save_embedding_to_speaker(speaker, embedding)

        # تحميلها مرة أخرى
        loaded = load_embedding_from_speaker(speaker)
        logger.info(f"Loaded embedding shape: {loaded.shape}")

        # مقارنة مع نفسها
        is_same, score = compare_embeddings(embedding, loaded)
        logger.info(f"Self comparison - Same: {is_same}, Score: {score}")

        return True
    else:
        logger.warning("No speakers with audio files found")
        return False