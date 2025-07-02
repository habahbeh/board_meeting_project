# audio_processing/utils/preprocessing.py

import os
import librosa
import numpy as np
from pydub import AudioSegment
from pydub.silence import split_on_silence


def convert_audio_to_wav(audio_file_path, output_dir=None):
    """
    تحويل أي ملف صوتي إلى صيغة WAV للمعالجة
    """
    if output_dir is None:
        output_dir = os.path.dirname(audio_file_path)

    filename = os.path.basename(audio_file_path)
    name, _ = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}.wav")

    audio = AudioSegment.from_file(audio_file_path)
    audio = audio.set_channels(1)  # تحويل إلى أحادي القناة
    audio = audio.set_frame_rate(16000)  # تعيين معدل العينات إلى 16kHz
    audio.export(output_path, format="wav")

    return output_path


def enhance_audio_quality(audio_file_path, output_dir=None):
    """
    تحسين جودة الصوت وإزالة الضوضاء
    """
    if output_dir is None:
        output_dir = os.path.dirname(audio_file_path)

    filename = os.path.basename(audio_file_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}_enhanced{ext}")

    # تحميل الصوت
    audio = AudioSegment.from_file(audio_file_path)

    # تطبيع مستوى الصوت
    normalized_audio = audio.normalize()

    # تحسين الوضوح
    enhanced_audio = normalized_audio.high_pass_filter(80).low_pass_filter(10000)

    # حفظ الملف المحسن
    enhanced_audio.export(output_path, format=ext.replace(".", ""))

    return output_path


def split_audio_by_silence(audio_file_path, output_dir=None, min_silence_len=500, silence_thresh=-40):
    """
    تقسيم الصوت إلى مقاطع بناء على فترات الصمت
    """
    if output_dir is None:
        output_dir = os.path.dirname(audio_file_path)

    # تحميل الصوت
    audio = AudioSegment.from_file(audio_file_path)

    # تقسيم بناء على الصمت
    segments = split_on_silence(
        audio,
        min_silence_len=min_silence_len,  # طول الصمت بالميلي ثانية
        silence_thresh=silence_thresh,  # عتبة الصمت بالديسيبل
        keep_silence=100  # احتفظ بـ 100 ميلي ثانية من الصمت في بداية ونهاية كل مقطع
    )

    # حفظ المقاطع
    segment_paths = []
    for i, segment in enumerate(segments):
        segment_path = os.path.join(output_dir, f"segment_{i:04d}.wav")
        segment.export(segment_path, format="wav")
        segment_paths.append((segment_path, i, len(segment) / 1000.0))  # المسار، الترتيب، المدة بالثواني

    return segment_paths