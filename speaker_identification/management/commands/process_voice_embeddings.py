# speaker_identification/management/commands/process_voice_embeddings.py

from django.core.management.base import BaseCommand
from django.conf import settings
from speaker_identification.models import Speaker
from speaker_identification.utils.voice_embeddings import (
    extract_voice_embedding,
    save_embedding_to_speaker,
    process_all_speaker_embeddings
)
import os


class Command(BaseCommand):
    help = 'معالجة البصمات الصوتية لجميع المتحدثين'

    def add_arguments(self, parser):
        parser.add_argument(
            '--speaker-id',
            type=int,
            help='معالجة متحدث محدد فقط'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة معالجة حتى لو كانت البصمة موجودة'
        )

    def handle(self, *args, **options):
        speaker_id = options.get('speaker_id')
        force = options.get('force', False)

        if speaker_id:
            # معالجة متحدث واحد
            try:
                speaker = Speaker.objects.get(id=speaker_id)
                if not speaker.reference_audio:
                    self.stdout.write(
                        self.style.ERROR(f'المتحدث {speaker.name} ليس لديه ملف صوتي مرجعي')
                    )
                    return

                if speaker.voice_embedding and not force:
                    self.stdout.write(
                        self.style.WARNING(f'المتحدث {speaker.name} لديه بصمة صوتية بالفعل')
                    )
                    return

                self.stdout.write(f'معالجة {speaker.name}...')

                audio_path = speaker.reference_audio.path
                if os.path.exists(audio_path):
                    embedding = extract_voice_embedding(audio_path)
                    save_embedding_to_speaker(speaker, embedding)
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ تمت معالجة {speaker.name}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'الملف الصوتي غير موجود: {audio_path}')
                    )

            except Speaker.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'المتحدث رقم {speaker_id} غير موجود')
                )
        else:
            # معالجة جميع المتحدثين
            self.stdout.write('معالجة جميع المتحدثين...')

            if force:
                speakers = Speaker.objects.filter(reference_audio__isnull=False)
            else:
                speakers = Speaker.objects.filter(
                    reference_audio__isnull=False,
                    voice_embedding__isnull=True
                )

            total = speakers.count()
            self.stdout.write(f'عدد المتحدثين للمعالجة: {total}')

            processed = 0
            for i, speaker in enumerate(speakers, 1):
                try:
                    audio_path = speaker.reference_audio.path
                    if os.path.exists(audio_path):
                        self.stdout.write(f'[{i}/{total}] معالجة {speaker.name}...')

                        embedding = extract_voice_embedding(audio_path)
                        save_embedding_to_speaker(speaker, embedding)

                        processed += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ تمت معالجة {speaker.name}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'تخطي {speaker.name} - الملف غير موجود')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'خطأ في معالجة {speaker.name}: {str(e)}')
                    )

            self.stdout.write(
                self.style.SUCCESS(f'\nتمت معالجة {processed} من {total} متحدث')
            )

