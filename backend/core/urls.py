from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Restrict Django Technical Admin strictly to Super Administrators
admin.site.site_header = "Smart Access Control - System Administration"
admin.site.site_title = "Access Control Admin"
admin.site.index_title = "System Configuration & Security Portal"
admin.site.has_permission = lambda request: bool(
    request.user and request.user.is_authenticated and request.user.is_active and request.user.is_superuser
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.access_control.urls')),
    path('api/v1/face/', include('apps.face_recognition.urls')),
    path('api/v1/', include('apps.security_logs.urls')),
    path('', include('apps.frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


