# speaker_identification/utils/diarization.py

import torch
import numpy as np
from pyannote.audio import Pipeline
from django.conf import settings
import os


def perform_diarization(audio_file_path, num_speakers=None):
    """
    تقسيم الصوت حسب المتحدثين باستخدام pyannote.audio

    المخرجات:
    قائمة من التوبلات (speaker_id, start_time, end_time)
    """
    # تهيئة pipeline لـ diarization
    # ملاحظة: يتطلب هذا حساب في Hugging Face وتوكن وصول
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.0",
        use_auth_token=settings.HUGGINGFACE_TOKEN
    )

    # تشغيل diarization
    diarization = pipeline(audio_file_path, num_speakers=num_speakers)

    # تحويل النتائج إلى قائمة من التوبلات
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append((speaker, turn.start, turn.end))

    return segments


def match_speakers_with_database(audio_segments, reference_embeddings):
    """
    مطابقة المتحدثين مع قاعدة بيانات البصمات الصوتية

    المدخلات:
    - audio_segments: قائمة من التوبلات (segment_path, speaker_id, start_time, end_time)
    - reference_embeddings: قاموس {speaker_id: embedding}

    المخرجات:
    قائمة من التوبلات (matched_speaker_id, start_time, end_time, confidence)
    """
    # هذه دالة توضيحية فقط وتحتاج إلى التنفيذ الكامل مع SpeechBrain

    matched_segments = []

    # هنا يجب استخراج الـ embeddings من كل مقطع صوتي
    # ثم مقارنتها مع الـ reference_embeddings باستخدام cosine similarity

    # يمكن تنفيذ هذا باستخدام SpeechBrain كما يلي:
    """
    from speechbrain.pretrained import EncoderClassifier

    # تحميل نموذج استخراج الـ embeddings
    encoder = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")

    for segment_path, speaker_id, start_time, end_time in audio_segments:
        # استخراج الـ embedding من المقطع
        signal, fs = librosa.load(segment_path, sr=16000)
        signal = torch.tensor(signal).unsqueeze(0)
        embedding = encoder.encode_batch(signal)

        # حساب التشابه مع كل متحدث مرجعي
        best_match = None
        best_score = -1

        for ref_id, ref_embedding in reference_embeddings.items():
            # حساب cosine similarity
            similarity = torch.nn.functional.cosine_similarity(embedding, ref_embedding).item()

            if similarity > best_score:
                best_score = similarity
                best_match = ref_id

        # إضافة المقطع مع المتحدث المطابق
        matched_segments.append((best_match, start_time, end_time, best_score))
    """

    # نموذج مبسط للتوضيح فقط
    for segment in audio_segments:
        speaker_id, start_time, end_time = segment
        matched_segments.append((f"speaker_{speaker_id}", start_time, end_time, 0.95))

    return matched_segments