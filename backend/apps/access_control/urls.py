from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AccessVerifyView,
    AuthLoginView,
    AuthLogoutView,
    AuthStatusView,
    DashboardStatsView,
    UserViewSet,
    CardViewSet,
    DeviceViewSet,
    ScheduleViewSet,
    AccessRuleViewSet
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('cards', CardViewSet, basename='card')
router.register('devices', DeviceViewSet, basename='device')
router.register('schedules', ScheduleViewSet, basename='schedule')
router.register('rules', AccessRuleViewSet, basename='rule')

urlpatterns = [
    path('access/verify/', AccessVerifyView.as_view(), name='access-verify'),
    path('auth/login/', AuthLoginView.as_view(), name='auth-login'),
    path('auth/logout/', AuthLogoutView.as_view(), name='auth-logout'),
    path('auth/status/', AuthStatusView.as_view(), name='auth-status'),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('', include(router.urls)),
]

