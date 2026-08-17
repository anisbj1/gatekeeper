from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.access_control.urls')),
    path('api/v1/face/', include('apps.face_recognition.urls')),
    path('api/v1/', include('apps.security_logs.urls')),
    path('', include('apps.frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

