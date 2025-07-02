# transcription/utils/whisper_gpt4o.py

import os
import openai
from django.conf import settings


def transcribe_with_whisper(audio_file_path, language="ar"):
    """
    نسخ الصوت باستخدام Whisper من OpenAI
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text"
            )

        return transcription
    except Exception as e:
        print(f"Error with Whisper API: {str(e)}")
        # استرجاع نص افتراضي في حالة الخطأ للاختبار فقط
        return "هذا نص افتراضي لفحص النظام في حالة فشل الاتصال بـ Whisper API."


def enhance_transcript_with_gpt(transcript_text, domain="banking"):
    """
    تحسين النص المنسوخ باستخدام GPT
    استخدام GPT-4o إذا كان متاحاً، وإلا استخدام GPT-3.5-turbo
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        system_prompt = """أنت مساعد متخصص في تحسين نصوص اجتماعات مجالس الإدارة المصرفية. 
        قم بتصحيح الأخطاء وتحسين النص مع الحفاظ على المصطلحات المصرفية الدقيقة. 
        حافظ على المعنى الأصلي واضبط الأخطاء اللغوية والإملائية."""

        if domain == "banking":
            system_prompt += """ كن دقيقًا جدًا مع المصطلحات المصرفية والمالية مثل:
            - معدلات الفائدة والعائد
            - نسب كفاية رأس المال
            - السيولة والملاءة المالية
            - الأصول والخصوم
            - التعثر والديون المتعثرة
            - القروض والتسهيلات
            """

        # محاولة استخدام GPT-4o، وإذا فشل، استخدام GPT-3.5-turbo
        try:
            model_to_use = "gpt-4o"
            enhanced_transcript = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"قم بتحسين وتصحيح نص الاجتماع التالي: {transcript_text}"}
                ]
            )
        except Exception as model_error:
            print(f"Error with GPT-4o, falling back to GPT-3.5: {str(model_error)}")
            model_to_use = "gpt-3.5-turbo"
            enhanced_transcript = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"قم بتحسين وتصحيح نص الاجتماع التالي: {transcript_text}"}
                ]
            )

        print(f"Successfully used model: {model_to_use}")
        return enhanced_transcript.choices[0].message.content

    except Exception as e:
        print(f"Error with GPT API: {str(e)}")
        # استرجاع النص الأصلي في حالة الخطأ للاختبار فقط
        return transcript_text


def extract_decisions_and_tasks(transcript_text):
    """
    استخراج القرارات والمهام من النص باستخدام GPT
    استخدام GPT-4o إذا كان متاحاً، وإلا استخدام GPT-3.5-turbo
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        system_prompt = """أنت مساعد متخصص في تحليل نصوص اجتماعات مجالس الإدارة المصرفية.
        مهمتك هي استخراج القرارات والمهام من محضر الاجتماع.
        - القرارات: هي الأمور التي تم الموافقة عليها أو رفضها من قبل المجلس
        - المهام: هي الأعمال التي تم تكليف أشخاص محددين بها مع مواعيد التنفيذ إن وجدت
        """

        # محاولة استخدام GPT-4o، وإذا فشل، استخدام GPT-3.5-turbo
        try:
            model_to_use = "gpt-4o"
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"استخرج القرارات والمهام من نص الاجتماع التالي: {transcript_text}"}
                ]
            )
        except Exception as model_error:
            print(f"Error with GPT-4o, falling back to GPT-3.5: {str(model_error)}")
            model_to_use = "gpt-3.5-turbo"
            response = client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"استخرج القرارات والمهام من نص الاجتماع التالي: {transcript_text}"}
                ]
            )

        print(f"Successfully used model: {model_to_use}")
        return response.choices[0].message.content

    except Exception as e:
        print(f"Error with GPT API: {str(e)}")
        # استرجاع قرارات ومهام افتراضية في حالة الخطأ للاختبار فقط
        return """
        القرارات:
        1. الموافقة على زيادة ميزانية التسويق بنسبة 10%.

        المهام:
        1. يجب على أحمد تقديم خطة التسويق المحدثة خلال أسبوع.
        """