# test_openai.py
# اختبار OpenAI API - متوافق مع الإصدار 0.28.0

import os
import openai
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# الحصول على المفتاح
api_key = os.getenv("OPENAI_API_KEY")

print("=" * 50)
print("اختبار OpenAI API - الإصدار 0.28.0")
print("=" * 50)

if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in .env file!")
    print("Please add: OPENAI_API_KEY=sk-... to your .env file")
    exit(1)

print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")

# تكوين OpenAI
openai.api_key = api_key

# اختبار 1: GPT
print("\n1. Testing GPT (ChatCompletion)...")
try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "قل مرحبا باللغة العربية"}
        ],
        max_tokens=50
    )
    print("✓ GPT works! Response:", response['choices'][0]['message']['content'])
except Exception as e:
    print(f"❌ GPT Error: {str(e)}")

# اختبار 2: Whisper
print("\n2. Testing Whisper (Audio Transcription)...")
try:
    # البحث عن ملف صوتي موجود
    test_audio = None

    if os.path.exists("media/meeting_audio"):
        audio_files = [f for f in os.listdir("media/meeting_audio")
                       if f.endswith(('.mp3', '.wav', '.m4a'))]
        if audio_files:
            test_audio = os.path.join("media/meeting_audio", audio_files[0])

    if test_audio and os.path.exists(test_audio):
        print(f"Using audio file: {test_audio}")
        file_size = os.path.getsize(test_audio) / (1024 * 1024)  # MB
        print(f"File size: {file_size:.2f} MB")

        with open(test_audio, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ar"
            )

        print("✓ Whisper works!")
        print("Transcribed text (first 200 chars):", response['text'][:200], "...")
        print("Total length:", len(response['text']), "characters")
    else:
        print("⚠ No audio files found to test Whisper.")
        print("Creating a test with empty audio...")

        # إنشاء ملف صوتي فارغ للاختبار
        import wave
        import struct

        test_wav = "test_audio.wav"
        with wave.open(test_wav, 'w') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # كتابة ثانية واحدة من الصمت
            for _ in range(16000):
                wav_file.writeframes(struct.pack('h', 0))

        with open(test_wav, "rb") as audio_file:
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )
        print("✓ Whisper API is accessible (tested with empty audio)")

        os.remove(test_wav)

except Exception as e:
    print(f"❌ Whisper Error: {str(e)}")
    print(f"Error type: {type(e).__name__}")

# اختبار 3: التحقق من الإصدار
print("\n3. Checking OpenAI package version...")
try:
    import pkg_resources

    version = pkg_resources.get_distribution("openai").version
    print(f"OpenAI package version: {version}")

    if version.startswith("1."):
        print("⚠ You have the new version. The code needs to be updated.")
        print("Run: pip install openai==0.28.0")
    else:
        print("✓ You have the correct version for this code.")
except:
    print("Could not determine OpenAI package version")

print("\n" + "=" * 50)
print("الخلاصة:")
if api_key and api_key.startswith("sk-"):
    print("✓ المفتاح موجود ويبدو صحيحاً")
    print("✓ تأكد من: TESTING_MODE = False في settings.py")
    print("✓ أعد تشغيل الخادم: python manage.py runserver")
else:
    print("❌ المفتاح غير صحيح أو غير موجود")
print("=" * 50)