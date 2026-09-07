from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccessLogViewSet, AdminAuditLogViewSet

router = DefaultRouter()
router.register('logs/access', AccessLogViewSet, basename='access-log')
router.register('logs/audit', AdminAuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]

