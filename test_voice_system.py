# test_voice_system.py - اختبار شامل للنظام

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'board_meeting_project.settings')
django.setup()

from speaker_identification.models import Speaker
from transcription.models import Meeting
import sys

print("🧪 اختبار نظام المقارنة الصوتية التلقائية")
print("=" * 60)

# 1. فحص البيئة
print("\n1️⃣ فحص البيئة:")
checks = {
    "HUGGINGFACE_TOKEN": os.getenv("HUGGINGFACE_TOKEN"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
}

all_ok = True
for key, value in checks.items():
    if value:
        print(f"✅ {key}: {value[:10]}...{value[-4:]}")
    else:
        print(f"❌ {key}: غير موجود!")
        all_ok = False

if not all_ok:
    print("\n❌ أصلح المتغيرات المفقودة في .env")
    sys.exit(1)

# 2. فحص المكتبات
print("\n2️⃣ فحص المكتبات:")
try:
    import pyannote.audio

    print(f"✅ pyannote.audio: {pyannote.audio.__version__}")
except:
    print("❌ pyannote.audio غير مثبت")
    print("Run: pip install pyannote.audio==3.1.1")
    sys.exit(1)

try:
    import torch

    print(f"✅ PyTorch: {torch.__version__}")
    print(f"   CUDA: {'نعم' if torch.cuda.is_available() else 'لا'}")
except:
    print("❌ PyTorch غير مثبت")
    sys.exit(1)

# 3. فحص المتحدثين
print("\n3️⃣ فحص المتحدثين:")
speakers = Speaker.objects.filter(reference_audio__isnull=False)
print(f"📊 متحدثين بملفات صوتية: {speakers.count()}")

if speakers.count() == 0:
    print("⚠️ لا يوجد متحدثين بملفات صوتية!")
    print("\n📝 إنشاء متحدثين تجريبيين...")

    # إنشاء متحدثين تجريبيين
    test_speakers = [
        ("د. أحمد محمد", "رئيس مجلس الإدارة"),
        ("أ. سارة خالد", "المدير المالي"),
        ("م. فاطمة علي", "المدير التنفيذي")
    ]

    for name, position in test_speakers:
        Speaker.objects.get_or_create(
            name=name,
            defaults={'position': position, 'speaker_type': 'board'}
        )
        print(f"✅ أنشئ: {name}")
else:
    print("\n👥 المتحدثون الموجودون:")
    for s in speakers[:5]:
        size_mb = s.reference_audio.size / (1024 * 1024) if s.reference_audio else 0
        print(f"   - {s.name}: {s.reference_audio.name} ({size_mb:.1f} MB)")

# 4. اختبار استخراج البصمات
print("\n4️⃣ اختبار استخراج البصمات الصوتية:")
try:
    from speaker_identification.utils.voice_comparison import (
        extract_speaker_embedding,
        save_speaker_embedding
    )

    test_speaker = speakers.first()
    if test_speaker:
        print(f"⏳ اختبار مع: {test_speaker.name}")
        embedding = extract_speaker_embedding(test_speaker.reference_audio.path)

        if embedding is not None:
            print(f"✅ تم استخراج البصمة! الشكل: {embedding.shape}")

            # حفظ البصمة
            if save_speaker_embedding(test_speaker):
                print("✅ تم حفظ البصمة في قاعدة البيانات")
            else:
                print("❌ فشل حفظ البصمة")
        else:
            print("❌ فشل استخراج البصمة")
    else:
        print("⚠️ لا يوجد متحدث للاختبار")

except Exception as e:
    print(f"❌ خطأ: {str(e)}")
    import traceback

    traceback.print_exc()

# 5. اختبار المعالجة
print("\n5️⃣ اختبار معالجة اجتماع:")
meeting = Meeting.objects.last()

if meeting:
    print(f"📁 اجتماع: {meeting.title}")
    print(f"🎵 ملف: {meeting.audio_file.name}")

    choice = input("\n🎯 هل تريد معالجة هذا الاجتماع؟ (y/n): ")

    if choice.lower() == 'y':
        print("\n⏳ جاري المعالجة (قد تأخذ عدة دقائق)...")

        try:
            from process_with_voice import process_meeting_auto

            # إعادة تعيين الحالة
            meeting.processed = False
            meeting.save()

            # معالجة
            success = process_meeting_auto(meeting.id)

            if success:
                print("\n✅ تمت المعالجة بنجاح!")

                # عرض النتائج
                from transcription.models import TranscriptSegment

                segments = TranscriptSegment.objects.filter(meeting=meeting)

                print(f"\n📊 النتائج:")
                print(f"   - عدد المقاطع: {segments.count()}")

                # عدد المتحدثين المختلفين
                speakers = segments.values_list('speaker__name', flat=True).distinct()
                print(f"   - عدد المتحدثين: {speakers.count()}")
                print(f"   - المتحدثون: {', '.join(speakers[:5])}")

            else:
                print("\n❌ فشلت المعالجة")

        except Exception as e:
            print(f"\n❌ خطأ: {str(e)}")
            import traceback

            traceback.print_exc()
else:
    print("⚠️ لا يوجد اجتماعات!")
    print("ارفع اجتماع أولاً من الواجهة")

print("\n" + "=" * 60)
print("✅ انتهى الاختبار!")

# نصائح
print("\n💡 نصائح:")
print("1. تأكد من رفع ملفات صوتية واضحة للمتحدثين (30 ثانية+)")
print("2. استخدم ملفات صوتية عالية الجودة للاجتماعات")
print("3. المعالجة الأولى تأخذ وقتاً لتحميل النماذج")
print("4. استخدم GPU لتسريع المعالجة إن أمكن")