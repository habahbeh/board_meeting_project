#!/usr/bin/env python
# test_voice_comparison.py - اختبار شامل للمقارنة الصوتية

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'board_meeting_project.settings')
django.setup()

from speaker_identification.models import Speaker
from transcription.models import Meeting
from speaker_identification.utils.voice_comparison import (
    extract_speaker_embedding,
    save_speaker_embedding,
    compare_embeddings,
    process_meeting_with_diarization,
    test_voice_comparison
)


def main():
    print("🧪 اختبار نظام المقارنة الصوتية")
    print("=" * 60)

    # 1. فحص المتطلبات
    print("\n1️⃣ فحص المتطلبات:")

    hf_token = os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("❌ HUGGINGFACE_TOKEN غير موجود!")
        print("أضف في .env: HUGGINGFACE_TOKEN=hf_...")
        sys.exit(1)
    else:
        print(f"✅ Hugging Face token: {hf_token[:10]}...{hf_token[-4:]}")

    # 2. اختبار استخراج البصمات
    print("\n2️⃣ اختبار استخراج البصمات الصوتية:")

    speaker = Speaker.objects.filter(reference_audio__isnull=False).first()
    if speaker:
        print(f"   اختبار مع: {speaker.name}")

        try:
            embedding = extract_speaker_embedding(speaker.reference_audio.path)
            if embedding is not None:
                print(f"   ✅ تم استخراج البصمة! الشكل: {embedding.shape}")

                # حفظ البصمة
                if save_speaker_embedding(speaker):
                    print("   ✅ تم حفظ البصمة")

                    # مقارنة مع نفسها
                    similarity = compare_embeddings(embedding, embedding)
                    print(f"   ✅ التشابه مع نفسها: {similarity:.3f} (يجب أن يكون 1.0)")
                else:
                    print("   ❌ فشل حفظ البصمة")
            else:
                print("   ❌ فشل استخراج البصمة")
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
    else:
        print("   ⚠️ لا يوجد متحدثين بملفات صوتية")
        print("   أضف متحدثين من: http://localhost:8000/speakers/")

    # 3. اختبار diarization
    print("\n3️⃣ اختبار Speaker Diarization:")

    meeting = Meeting.objects.last()
    if meeting and meeting.audio_file:
        print(f"   اختبار مع: {meeting.title}")

        try:
            print("   ⏳ جاري المعالجة (قد تأخذ دقيقة)...")
            segments = process_meeting_with_diarization(meeting.audio_file.path)

            if segments:
                print(f"   ✅ تم إيجاد {len(segments)} مقطع")

                # عرض أول 3 مقاطع
                print("\n   📊 عينة من النتائج:")
                for i, seg in enumerate(segments[:3]):
                    print(f"      {i + 1}. {seg['speaker'].name}: "
                          f"{seg['start']:.1f}s - {seg['end']:.1f}s")
            else:
                print("   ❌ لم يتم إيجاد مقاطع")
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("   ⚠️ لا يوجد اجتماعات")
        print("   ارفع اجتماع من: http://localhost:8000/audio/upload/")

    # 4. اختبار المقارنة بين متحدثين
    print("\n4️⃣ اختبار المقارنة بين المتحدثين:")

    speakers = list(Speaker.objects.filter(
        reference_audio__isnull=False,
        voice_embedding__isnull=False
    )[:2])

    if len(speakers) >= 2:
        from speaker_identification.utils.voice_comparison import load_speaker_embedding

        emb1 = load_speaker_embedding(speakers[0])
        emb2 = load_speaker_embedding(speakers[1])

        if emb1 is not None and emb2 is not None:
            similarity = compare_embeddings(emb1, emb2)
            print(f"   التشابه بين {speakers[0].name} و {speakers[1].name}: {similarity:.3f}")

            if similarity > 0.7:
                print("   ⚠️ التشابه عالي! قد يكونان نفس الشخص")
            else:
                print("   ✅ متحدثان مختلفان")
    else:
        print("   ⚠️ يجب وجود متحدثين على الأقل مع بصمات صوتية")

    # 5. نصائح
    print("\n💡 نصائح للاستخدام:")
    print("1. ارفع ملفات صوتية واضحة للمتحدثين (30 ثانية+)")
    print("2. استخدم: python process_with_voice.py")
    print("3. أو: python manage.py process_with_voice")
    print("4. شاهد النتائج في: http://localhost:8000/transcription/")

    print("\n✅ انتهى الاختبار!")


if __name__ == "__main__":
    # اختبار الوحدة أولاً
    print("\n🔧 اختبار وحدة voice_comparison...")
    test_voice_comparison()

    print("\n" + "=" * 60)

    # ثم الاختبار الشامل
    main()