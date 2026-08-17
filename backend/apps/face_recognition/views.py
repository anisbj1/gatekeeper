import logging
from uuid import UUID
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication
from apps.access_control.models import Device, Card
from apps.access_control.permissions import HasValidDeviceToken
from .serializers import (
    EnrollmentStartSerializer,
    EnrollmentUploadSerializer,
    BiometricVerifySerializer
)
from .services import EnrollmentService, VerificationService
from .models import EnrollmentSession, FaceProfile

logger = logging.getLogger(__name__)

class EnrollmentStartView(APIView):
    permission_classes = [HasValidDeviceToken]

    def post(self, request, *args, **kwargs):
        serializer = EnrollmentStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        card_uid = serializer.validated_data['card_uid']
        device_id = serializer.validated_data['device_id']

        try:
            card = Card.objects.select_related('user').get(uid=card_uid)
            if not card.is_active or not card.user.is_active:
                return Response(
                    {"error": "Card or user is inactive"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            user = card.user
        except Card.DoesNotExist:
            return Response(
                {"error": "RFID card not registered"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            device = Device.objects.get(device_id=device_id)
            if not device.is_active:
                return Response(
                    {"error": "Device is inactive"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Device.DoesNotExist:
            return Response(
                {"error": "Device not registered"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        session = EnrollmentService.start_session(user=user, device=device)
        
        return Response({
            "session_id": str(session.id),
            "status": session.status,
            "images_required": session.images_required,
            "username": user.username
        }, status=status.HTTP_201_CREATED)


class EnrollmentUploadView(APIView):
    permission_classes = [HasValidDeviceToken]

    def post(self, request, *args, **kwargs):
        serializer = EnrollmentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session_id = serializer.validated_data['session_id']
        device_id = serializer.validated_data['device_id']
        image_file = serializer.validated_data['image']

        try:
            session = EnrollmentSession.objects.get(id=session_id)
        except (EnrollmentSession.DoesNotExist, ValueError):
            return Response(
                {"error": "Enrollment session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if session.device.device_id != device_id:
            return Response(
                {"error": "Device ID does not match session"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            image_bytes = image_file.read()
            res = EnrollmentService.process_frame(session, image_bytes)
        except Exception as e:
            logger.error(f"Error during enrollment upload processing: {str(e)}")
            return Response(
                {"error": "Internal server error during biometric processing"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not res["success"]:
            # Quality check failed
            return Response({
                "session_id": str(session_id),
                "status": session.status,
                "error_code": res.get("error_code"),
                "message": res["message"],
                "images_collected": res.get("images_collected"),
                "images_required": res.get("images_required")
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Success - frame accepted
        # Determine status code (201 if session is complete, 200 otherwise)
        status_code = status.HTTP_201_CREATED if res["status"] == 'COMPLETED' else status.HTTP_200_OK

        return Response({
            "session_id": str(session_id),
            "status": res["status"],
            "images_collected": res["images_collected"],
            "images_required": res["images_required"],
            "message": res["message"]
        }, status=status_code)


class EnrollmentStatusView(APIView):
    permission_classes = [HasValidDeviceToken]

    def get(self, request, session_id, *args, **kwargs):
        try:
            session = EnrollmentSession.objects.get(id=session_id)
        except (EnrollmentSession.DoesNotExist, ValueError):
            return Response(
                {"error": "Enrollment session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Check expiration
        if session.status in ['PENDING', 'COLLECTING'] and timezone.now() > session.expires_at:
            session.status = 'EXPIRED'
            session.save()

        return Response({
            "session_id": str(session.id),
            "status": session.status,
            "images_collected": session.images_collected,
            "images_required": session.images_required,
            "expires_at": session.expires_at.isoformat()
        }, status=status.HTTP_200_OK)


class BiometricVerifyView(APIView):
    permission_classes = [HasValidDeviceToken]

    def post(self, request, *args, **kwargs):
        serializer = BiometricVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        card_uid = serializer.validated_data['card_uid']
        device_id = serializer.validated_data['device_id']
        image_file = serializer.validated_data['image']

        try:
            image_bytes = image_file.read()
            result = VerificationService.verify_face(
                card_uid=card_uid,
                device_id=device_id,
                image_bytes=image_bytes
            )
        except Exception as e:
            logger.error(f"Error during biometric verification: {str(e)}")
            return Response(
                {"authorized": False, "message": "Biometric pipeline failure", "action": "keep_locked"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not result["authorized"]:
            if "error_code" in result:
                # Processing/quality fail (e.g. no face, blurry)
                return Response(result, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            else:
                # Biometric mismatch
                return Response(result, status=status.HTTP_403_FORBIDDEN)

        # Match succeeded!
        return Response(result, status=status.HTTP_200_OK)


class BiometricProfileView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, username, *args, **kwargs):
        try:
            user = User.objects.get(username=username)
            profile = user.face_profile
        except (User.DoesNotExist, FaceProfile.DoesNotExist):
            return Response(
                {"error": "Biometric profile not found for user"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        ref_image = profile.images.filter(is_reference=True).first()
        ref_image_url = request.build_absolute_uri(ref_image.cropped_image.url) if ref_image else None

        return Response({
            "username": username,
            "is_biometric_active": profile.is_biometric_active,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "embeddings_count": profile.embeddings.count(),
            "images_count": profile.images.count(),
            "reference_image_url": ref_image_url
        }, status=status.HTTP_200_OK)

    def delete(self, request, username, *args, **kwargs):
        try:
            user = User.objects.get(username=username)
            profile = user.face_profile
        except (User.DoesNotExist, FaceProfile.DoesNotExist):
            return Response(
                {"error": "Biometric profile not found for user"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Deleting profile deletes all associated FaceImage files via CASCADE
        # However, Django's default CASCADE delete on model does not delete file from disk.
        # Let's delete the physical files first to avoid orphans.
        for face_img in profile.images.all():
            if face_img.original_image:
                face_img.original_image.delete(save=False)
            if face_img.cropped_image:
                face_img.cropped_image.delete(save=False)

        profile.delete()
        return Response(
            {"message": f"Biometric profile and files deleted successfully for {username}"}, 
            status=status.HTTP_200_OK
        )


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

@method_decorator(ensure_csrf_cookie, name='dispatch')
class EnrollmentPortalView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'face_recognition/enroll.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all().order_by('username')
        return context


class WebEnrollmentStartView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        card_uid = request.data.get('card_uid')

        if not username or not card_uid:
            return Response(
                {"error": "Username and Card UID are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Standardize card UID formatting
        cleaned_uid = card_uid.replace(':', '').replace(' ', '').upper()
        import re
        if not re.match(r'^[0-9A-F]{8,32}$', cleaned_uid):
            return Response(
                {"error": "Card UID must be a valid hexadecimal string of length 8 to 32 characters (4 to 16 bytes)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Handle Card Registration / Assignment
        try:
            card = Card.objects.get(uid=cleaned_uid)
            if card.user != user:
                return Response(
                    {"error": f"Card UID {cleaned_uid} is already registered to user {card.user.username}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Make sure it's active
            if not card.is_active:
                card.is_active = True
                card.save()
        except Card.DoesNotExist:
            # Create a new card linked to the user
            card = Card.objects.create(
                uid=cleaned_uid,
                user=user,
                is_active=True
            )

        # Lookup device or create a dummy device for web portal logs
        device = Device.objects.filter(is_active=True).first()
        if not device:
            device, _ = Device.objects.get_or_create(
                device_id='web_portal',
                defaults={'name': 'Web Enrollment Portal', 'is_active': True}
            )

        # Start Session
        session = EnrollmentService.start_session(user=user, device=device)
        session.images_required = 3  # Front, Left side, Right side
        session.save()

        return Response({
            "session_id": str(session.id),
            "status": session.status,
            "images_required": session.images_required,
            "username": user.username
        }, status=status.HTTP_201_CREATED)


class WebEnrollmentUploadView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        session_id = request.data.get('session_id')
        image_file = request.FILES.get('image')

        if not session_id or not image_file:
            return Response(
                {"error": "Session ID and Image file are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = EnrollmentSession.objects.get(id=session_id)
        except (EnrollmentSession.DoesNotExist, ValueError):
            return Response(
                {"error": "Enrollment session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            image_bytes = image_file.read()
            res = EnrollmentService.process_frame(session, image_bytes)
        except Exception as e:
            logger.error(f"Error during web enrollment upload: {str(e)}")
            return Response(
                {"error": "Internal server error during biometric processing"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not res["success"]:
            return Response({
                "session_id": str(session_id),
                "status": session.status,
                "error_code": res.get("error_code"),
                "message": res["message"],
                "images_collected": res.get("images_collected"),
                "images_required": res.get("images_required")
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        status_code = status.HTTP_201_CREATED if res["status"] == 'COMPLETED' else status.HTTP_200_OK

        return Response({
            "session_id": str(session_id),
            "status": res["status"],
            "images_collected": res["images_collected"],
            "images_required": res["images_required"],
            "message": res["message"]
        }, status=status_code)


from rest_framework import viewsets
from .models import RecognitionAttempt, FaceProfile
from .serializers import RecognitionAttemptSerializer, FaceProfileSerializer
from django.db.models import Q

class BiometricAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    queryset = RecognitionAttempt.objects.all().order_by('-timestamp')
    serializer_class = RecognitionAttemptSerializer

    def get_queryset(self):
        queryset = RecognitionAttempt.objects.all().order_by('-timestamp')
        device_id = self.request.query_params.get('device')
        if device_id:
            queryset = queryset.filter(device__device_id__icontains=device_id)
            
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username__icontains=username)
            
        authorized = self.request.query_params.get('authorized')
        if authorized is not None:
            queryset = queryset.filter(authorized=authorized.lower() == 'true')
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(device__device_id__icontains=search)
            )
        return queryset


class FaceProfileViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    queryset = FaceProfile.objects.all().order_by('-created_at')
    serializer_class = FaceProfileSerializer

    def get_queryset(self):
        queryset = FaceProfile.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        return queryset

    def perform_destroy(self, instance):
        # Delete original and cropped files to avoid orphans
        for face_img in instance.images.all():
            if face_img.original_image:
                face_img.original_image.delete(save=False)
            if face_img.cropped_image:
                face_img.cropped_image.delete(save=False)
        instance.delete()


