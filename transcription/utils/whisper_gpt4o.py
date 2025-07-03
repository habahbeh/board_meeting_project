# transcription/utils/whisper_gpt4o.py

import os
import openai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# تكوين مكتبة OpenAI - للإصدار 0.28.0
if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
    openai.api_key = settings.OPENAI_API_KEY
    print(f"OpenAI API Key configured: {openai.api_key[:10]}...")
else:
    raise Exception("OPENAI_API_KEY not found in settings!")


def transcribe_with_whisper(audio_file_path, language="ar"):
    """
    نسخ الصوت باستخدام Whisper من OpenAI
    """
    print(f"Starting Whisper transcription for: {audio_file_path}")

    # التأكد من وجود الملف
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

    try:
        # استخدام Whisper API - الإصدار القديم
        with open(audio_file_path, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language=language
            )

        print(f"Whisper transcription successful!")
        print(f"Transcribed text: {response['text'][:100]}...")

        # تقسيم النص إلى مقاطع
        text = response['text']
        sentences = text.split('.')
        segments = []
        current_time = 0

        for sentence in sentences:
            if sentence.strip():
                # حساب وقت تقريبي بناءً على طول الجملة
                words_count = len(sentence.split())
                segment_duration = max(5, words_count * 0.5)  # نصف ثانية لكل كلمة

                segments.append({
                    'start': current_time,
                    'end': current_time + segment_duration,
                    'text': sentence.strip() + '.'
                })
                current_time += segment_duration

        return {'text': text, 'segments': segments}

    except Exception as e:
        logger.error(f"CRITICAL Whisper API Error: {str(e)}")
        raise Exception(f"Whisper API failed: {str(e)}")


def identify_speaker_from_text(text):
    """
    تحديد المتحدث من النص بناءً على الأنماط الشائعة
    """
    # قائمة بالأنماط الشائعة لتعريف المتحدث
    speaker_patterns = [
        # الأنماط العربية
        ('أنا', 'after'),  # "أنا د. أحمد"
        ('معكم', 'after'),  # "معكم د. أحمد"
        ('يتحدث', 'before'),  # "د. أحمد يتحدث"
        ('دكتور', 'with'),  # "دكتور أحمد"
        ('المهندس', 'with'),
        ('الأستاذ', 'with'),
        ('السيد', 'with'),
        ('السيدة', 'with'),
        ('المدير', 'with'),

        # البحث عن الأسماء بعد العبارات الشائعة
        ('شكراً', 'speaker_change'),
        ('السلام عليكم', 'speaker_change'),
        ('أعطي الكلمة', 'speaker_change'),
    ]

    text_lower = text.lower()

    for pattern, position in speaker_patterns:
        if pattern in text_lower:
            words = text.split()

            for i, word in enumerate(words):
                if word.lower() == pattern:
                    if position == 'after' and i + 1 < len(words):
                        # الاسم يأتي بعد النمط
                        potential_name = []
                        for j in range(i + 1, min(i + 4, len(words))):
                            potential_name.append(words[j])
                            if words[j].endswith('.') or words[j].endswith(','):
                                break
                        return ' '.join(potential_name).strip('.,،')

                    elif position == 'with' and i + 1 < len(words):
                        # النمط جزء من الاسم
                        return ' '.join([words[i], words[i + 1]]).strip('.,،')

    return None


def enhance_transcript_with_gpt(transcript_data, domain="banking"):
    """
    تحسين النص المنسوخ مع تحديد المتحدثين باستخدام GPT
    """
    print("Enhancing transcript with speaker identification...")

    try:
        if isinstance(transcript_data, dict):
            segments = transcript_data.get('segments', [])
            full_text = transcript_data.get('text', '')
        else:
            segments = []
            full_text = transcript_data

        # محاولة استخدام GPT لتحديد المتحدثين
        try:
            # استخدام ChatGPT لتحليل النص
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """أنت مساعد متخصص في تحليل محاضر الاجتماعات.
                        مهمتك: تحديد المتحدثين في النص.
                        ابحث عن:
                        1. عبارات التعريف بالنفس (أنا فلان، معكم فلان)
                        2. عبارات تغيير المتحدث (أعطي الكلمة لـ، شكراً)
                        3. الأسماء والمناصب

                        أرجع قائمة بالمتحدثين وما قالوه."""
                    },
                    {
                        "role": "user",
                        "content": f"حلل هذا النص وحدد المتحدثين:\n{full_text[:2000]}"
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )

            gpt_analysis = response['choices'][0]['message']['content']
            print(f"GPT Analysis: {gpt_analysis[:200]}...")

        except Exception as gpt_error:
            print(f"GPT enhancement failed: {gpt_error}")
            # استمر بالمعالجة اليدوية

        # معالجة المقاطع لتحديد المتحدثين
        enhanced_segments = []
        current_speaker = "غير معروف"

        for i, segment in enumerate(segments):
            text = segment['text']

            # محاولة تحديد المتحدث من النص
            identified_speaker = identify_speaker_from_text(text)
            if identified_speaker:
                current_speaker = identified_speaker
                print(f"Identified speaker: {current_speaker}")

            # البحث عن إشارات تغيير المتحدث
            if any(phrase in text for phrase in ['أعطي الكلمة', 'شكراً دكتور', 'شكراً أستاذ']):
                # قد يكون هناك متحدث جديد في المقطع التالي
                print(f"Speaker change detected in: {text[:50]}...")

            enhanced_segments.append({
                'start': segment['start'],
                'end': segment['end'],
                'text': text,
                'speaker': current_speaker
            })

        print(f"Enhanced {len(enhanced_segments)} segments")
        return enhanced_segments

    except Exception as e:
        logger.error(f"Error in enhance_transcript_with_gpt: {str(e)}")
        raise Exception(f"Enhancement failed: {str(e)}")


def extract_decisions_and_tasks(segments):
    """
    استخراج القرارات والمهام من المقاطع
    """
    print("Extracting decisions and tasks...")

    decisions = []
    tasks = []

    decision_keywords = [
        'القرار', 'نصدر القرار', 'تقرر', 'الموافقة على', 'رفض',
        'تم اعتماد', 'نوافق', 'تمت الموافقة', 'يُقر', 'يُعتمد'
    ]

    task_keywords = [
        'مهمة', 'نكلف', 'يجب على', 'مطلوب من', 'يتولى',
        'المسؤول عن', 'يقوم ب', 'تكليف', 'مسؤولية'
    ]

    for segment in segments:
        text = segment.get('text', '')

        # التحقق من القرارات
        for keyword in decision_keywords:
            if keyword in text:
                decisions.append({
                    'text': text,
                    'speaker': segment.get('speaker', 'غير معروف'),
                    'time': segment.get('start', 0)
                })
                print(f"Found decision: {text[:50]}...")
                break

        # التحقق من المهام
        for keyword in task_keywords:
            if keyword in text:
                # محاولة استخراج اسم المكلف
                assignee = None
                if 'نكلف' in text or 'مهمة ل' in text:
                    words = text.split()
                    for i, word in enumerate(words):
                        if word in ['نكلف', 'مهمة'] and i + 1 < len(words):
                            assignee = words[i + 1]
                            if i + 2 < len(words) and not words[i + 2].startswith('ب'):
                                assignee += ' ' + words[i + 2]

                tasks.append({
                    'text': text,
                    'speaker': segment.get('speaker', 'غير معروف'),
                    'assignee': assignee,
                    'time': segment.get('start', 0)
                })
                print(f"Found task for {assignee}: {text[:50]}...")
                break

    print(f"Extracted {len(decisions)} decisions and {len(tasks)} tasks")

    # محاولة استخدام GPT لتحسين استخراج القرارات والمهام
    try:
        full_text = '\n'.join([s['text'] for s in segments])

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """استخرج القرارات والمهام من محضر الاجتماع.
                    القرارات: ما تم الموافقة عليه أو رفضه
                    المهام: ما تم تكليف شخص به
                    اذكر اسم المسؤول عن كل مهمة."""
                },
                {
                    "role": "user",
                    "content": f"استخرج القرارات والمهام:\n{full_text[:2000]}"
                }
            ],
            max_tokens=500,
            temperature=0.3
        )

        gpt_extraction = response['choices'][0]['message']['content']
        print(f"GPT Extraction: {gpt_extraction[:200]}...")

    except Exception as e:
        print(f"GPT extraction failed: {e}")

    return {
        'decisions': decisions,
        'tasks': tasks
    }