# setup_voice_system.py - إعداد نظام المقارنة الصوتية

import os
import sys

print("🚀 إعداد نظام المقارنة الصوتية التلقائية")
print("="*50)

# 1. التحقق من المتطلبات
print("\n1️⃣ فحص المتطلبات...")

# التحقق من Hugging Face Token
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if not hf_token:
    print("❌ HUGGINGFACE_TOKEN غير موجود!")
    print("\n📝 الخطوات:")
    print("1. اذهب إلى: https://huggingface.co/settings/tokens")
    print("2. أنشئ token جديد")
    print("3. أضف في .env:")
    print("   HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxx")
    sys.exit(1)
else:
    print(f"✅ Hugging Face token: {hf_token[:10]}...{hf_token[-4:]}")

# التحقق من OpenAI
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("❌ OPENAI_API_KEY غير موجود!")
    sys.exit(1)
else:
    print(f"✅ OpenAI key: {openai_key[:10]}...{openai_key[-4:]}")

# 2. التحقق من المكتبات
print("\n2️⃣ فحص المكتبات...")
try:
    import pyannote.audio
    print("✅ pyannote.audio مثبت")
except:
    print("❌ pyannote.audio غير مثبت!")
    print("Run: pip install pyannote.audio==3.1.1")
    sys.exit(1)

try:
    import torch
    print(f"✅ PyTorch مثبت (CUDA: {torch.cuda.is_available()})")
except:
    print("❌ PyTorch غير مثبت!")
    sys.exit(1)

# 3. إعداد Django
print("\n3️⃣ إعداد Django...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'board_meeting_project.settings')
import django
django.setup()

# 4. إنشاء المجلدات
print("\n4️⃣ إنشاء المجلدات...")
dirs = [
    'speaker_identification/utils',
    'models/speaker_encoder',
    'logs'
]

for dir_path in dirs:
    os.makedirs(dir_path, exist_ok=True)
    print(f"✅ {dir_path}")

# 5. التأكد من وجود __init__.py
init_files = [
    'speaker_identification/__init__.py',
    'speaker_identification/utils/__init__.py'
]

for init_file in init_files:
    if not os.path.exists(init_file):
        open(init_file, 'a').close()
        print(f"✅ Created {init_file}")

# 6. فحص المتحدثين
print("\n5️⃣ فحص المتحدثين...")
from speaker_identification.models import Speaker

speakers = Speaker.objects.all()
speakers_with_audio = speakers.filter(reference_audio__isnull=False)

print(f"📊 إجمالي المتحدثين: {speakers.count()}")
print(f"🎤 متحدثين بملفات صوتية: {speakers_with_audio.count()}")

if speakers_with_audio.count() == 0:
    print("\n⚠️ تحذير: لا يوجد متحدثين بملفات صوتية!")
    print("يجب رفع ملفات صوتية مرجعية للمتحدثين أولاً")
else:
    print("\n👥 المتحدثون:")
    for s in speakers_with_audio:
        print(f"   - {s.name} ({s.reference_audio.name})")

# 7. اختبار سريع
print("\n6️⃣ اختبار النظام...")
try:
    from speaker_identification.utils.voice_comparison import get_embedding_model
    print("⏳ جاري تحميل النموذج (قد يأخذ دقيقة)...")
    model = get_embedding_model()
    print("✅ النموذج يعمل!")
except Exception as e:
    print(f"❌ خطأ: {str(e)}")

print("\n" + "="*50)
print("✅ النظام جاهز للعمل!")
print("\n🎯 لمعالجة اجتماع:")
print("   python process_with_voice.py")
print("\n📝 لمعالجة اجتماع محدد:")
print("   python process_with_voice.py [meeting_id]")
print("="*50)