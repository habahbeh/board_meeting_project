# Generated by Django 4.2 on 2025-07-01 20:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_title', models.CharField(blank=True, max_length=100, verbose_name='المسمى الوظيفي')),
                ('department', models.CharField(blank=True, max_length=100, verbose_name='القسم/الإدارة')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='رقم الهاتف')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'الملف الشخصي',
                'verbose_name_plural': 'الملفات الشخصية',
            },
        ),
    ]
