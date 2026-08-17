from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnrollmentStartView,
    EnrollmentUploadView,
    EnrollmentStatusView,
    BiometricVerifyView,
    BiometricProfileView,
    EnrollmentPortalView,
    WebEnrollmentStartView,
    WebEnrollmentUploadView,
    BiometricAttemptViewSet,
    FaceProfileViewSet
)

router = DefaultRouter()
router.register('logs/biometric', BiometricAttemptViewSet, basename='biometric-attempt')
router.register('profiles', FaceProfileViewSet, basename='face-profile')

urlpatterns = [
    path('enroll/', EnrollmentPortalView.as_view(), name='enroll-portal'),
    path('enroll/start/', EnrollmentStartView.as_view(), name='enroll-start'),
    path('enroll/upload/', EnrollmentUploadView.as_view(), name='enroll-upload'),
    path('enroll/status/<uuid:session_id>/', EnrollmentStatusView.as_view(), name='enroll-status'),
    path('web-enroll/start/', WebEnrollmentStartView.as_view(), name='web-enroll-start'),
    path('web-enroll/upload/', WebEnrollmentUploadView.as_view(), name='web-enroll-upload'),
    path('verify/', BiometricVerifyView.as_view(), name='biometric-verify'),
    path('profile/<str:username>/', BiometricProfileView.as_view(), name='biometric-profile'),
    path('', include(router.urls)),
]

