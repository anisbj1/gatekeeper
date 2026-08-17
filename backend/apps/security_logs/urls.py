from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccessLogViewSet

router = DefaultRouter()
router.register('logs/access', AccessLogViewSet, basename='access-log')

urlpatterns = [
    path('', include(router.urls)),
]
