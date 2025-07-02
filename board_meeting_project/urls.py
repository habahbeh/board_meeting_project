# board_meeting_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns, set_language  # إضافة استيراد set_language
from django.contrib.auth import views as auth_views
# URLs غير مترجمة
urlpatterns = [
    # إضافة مسار تغيير اللغة هنا - يجب أن يكون خارج i18n_patterns
    path('i18n/setlang/', set_language, name='set_language'),
]

# URLs مترجمة
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    # مسارات المصادقة
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='auth/logout.html'), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),
         name='password_reset_complete'),

    # مسارات التطبيقات
    path('', include('core.urls')),
    path('audio/', include('audio_processing.urls')),
    path('speakers/', include('speaker_identification.urls')),
    path('transcription/', include('transcription.urls')),
    path('business/', include('business_logic.urls')),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)