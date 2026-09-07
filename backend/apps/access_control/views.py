import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q

from .models import Device, Card, Schedule, AccessRule
from .serializers import (
    AccessVerifySerializer,
    UserSerializer,
    CardSerializer,
    DeviceSerializer,
    ScheduleSerializer,
    AccessRuleSerializer
)
from .services import AccessValidationService, UserSessionService
from .permissions import (
    HasValidDeviceToken,
    IsSuperAdminUser,
    IsOperationalAdminUser,
    CanManageUsersPermission,
    CanManageDevicesPermission
)
from apps.security_logs.models import AccessLog
from apps.security_logs.services import AdminAuditService
from apps.face_recognition.models import FaceProfile

try:
    from axes.handlers.proxy import AxesProxyHandler
    from axes.utils import reset as axes_reset
    from axes.models import AccessAttempt
    is_axes_locked = AxesProxyHandler.is_locked
except ImportError:
    is_axes_locked = lambda req: False
    axes_reset = lambda **kw: None
    AccessAttempt = None


class AccessVerifyView(APIView):
    permission_classes = [HasValidDeviceToken]

    def post(self, request, *args, **kwargs):
        serializer = AccessVerifySerializer(data=request.data)
        if serializer.is_valid():
            card_uid = serializer.validated_data['card_uid']
            device_id = serializer.validated_data['device_id']
            
            result = AccessValidationService.validate_scan(
                card_uid=card_uid,
                device_id=device_id
            )
            
            if result["authorized"]:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_403_FORBIDDEN)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # 1. Check if IP / client is currently locked out by Axes
        if is_axes_locked(request):
            return Response(
                {"error": "Too many failed login attempts. Your IP address is temporarily blocked for security."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                return Response({"error": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
            if not user.is_staff:
                return Response({"error": "Access restricted to staff members."}, status=status.HTTP_403_FORBIDDEN)
            
            login(request, user)
            now_ts = time.time()
            request.session['_session_created_at'] = now_ts
            request.session['_session_last_activity'] = now_ts

            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Check if this failure just triggered an Axes lockout
            if is_axes_locked(request):
                return Response(
                    {"error": "Too many failed login attempts. Your IP address has been temporarily blocked."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            # Check if user exists and password is correct, but account is disabled
            try:
                existing_user = User.objects.get(username=username)
                if existing_user.check_password(password) and not existing_user.is_active:
                    return Response({"error": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)
            except User.DoesNotExist:
                pass

            return Response({"error": "Invalid username or password."}, status=status.HTTP_401_UNAUTHORIZED)



class AuthLogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


class AuthStatusView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DashboardStatsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]

    def get(self, request, *args, **kwargs):
        today = timezone.localtime(timezone.now()).date()
        
        today_access_logs = AccessLog.objects.filter(timestamp__date=today)
        granted_today = today_access_logs.filter(authorized=True).count()
        denied_today = today_access_logs.filter(authorized=False).count()
        
        stats = {
            "employees_count": User.objects.count(),
            "cards_count": Card.objects.filter(is_active=True).count(),
            "devices_count": Device.objects.count(),
            "face_profiles_count": FaceProfile.objects.filter(is_biometric_active=True).count(),
            "today_granted_count": granted_today,
            "today_denied_count": denied_today,
            "today_attempts_count": today_access_logs.count()
        }
        return Response(stats, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [CanManageUsersPermission]
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | 
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) | 
                Q(email__icontains=search)
            )
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminUser])
    def lock(self, request, pk=None):
        """
        Locks/disables an account and immediately invalidates all active sessions.
        Restricted to Super Administrators.
        """
        user = self.get_object()
        if user == request.user:
            return Response({"error": "You cannot lock your own account."}, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_active = False
        user.save()

        # Invalidate active database sessions immediately
        UserSessionService.invalidate_user_sessions(user.id)

        AdminAuditService.log_event(
            event_type='ACCOUNT_LOCKED',
            actor=request.user.username,
            target_user=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            details=f"Account '{user.username}' locked by admin '{request.user.username}'."
        )

        return Response(
            {"message": f"Account '{user.username}' locked successfully and active sessions invalidated."},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminUser])
    def unlock(self, request, pk=None):
        """
        Unlocks/enables a disabled account.
        Restricted to Super Administrators.
        """
        user = self.get_object()
        user.is_active = True
        user.save()

        AdminAuditService.log_event(
            event_type='ACCOUNT_UNLOCKED',
            actor=request.user.username,
            target_user=user.username,
            ip_address=request.META.get('REMOTE_ADDR'),
            details=f"Account '{user.username}' unlocked by admin '{request.user.username}'."
        )

        return Response(
            {"message": f"Account '{user.username}' unlocked successfully."},
            status=status.HTTP_200_OK
        )


class CardViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]
    queryset = Card.objects.all().order_by('-created_at')
    serializer_class = CardSerializer

    def get_queryset(self):
        queryset = Card.objects.all().order_by('-created_at')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(uid__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class DeviceViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [CanManageDevicesPermission]
    queryset = Device.objects.all().order_by('device_id')
    serializer_class = DeviceSerializer

    def get_queryset(self):
        queryset = Device.objects.all().order_by('device_id')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(device_id__icontains=search) |
                Q(name__icontains=search)
            )
        return queryset


class ScheduleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]
    queryset = Schedule.objects.all().order_by('name')
    serializer_class = ScheduleSerializer

    def get_queryset(self):
        queryset = Schedule.objects.all().order_by('name')
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset


class AccessRuleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsOperationalAdminUser]
    queryset = AccessRule.objects.all().order_by('-created_at')
    serializer_class = AccessRuleSerializer

    def get_queryset(self):
        queryset = AccessRule.objects.all().order_by('-created_at')
        device_id = self.request.query_params.get('device')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class SecurityManagementViewSet(viewsets.ViewSet):
    """
    SuperAdmin endpoint for monitoring and unblocking locked-out IP addresses.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSuperAdminUser]

    @action(detail=False, methods=['get'])
    def blocked_ips(self, request):
        if AccessAttempt is None:
            return Response([], status=status.HTTP_200_OK)
            
        attempts = AccessAttempt.objects.all().order_by('-attempt_time')
        data = [
            {
                'ip_address': a.ip_address,
                'username': a.username,
                'failures_since_start': a.failures_since_start,
                'attempt_time': a.attempt_time,
            }
            for a in attempts
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def unblock_ip(self, request):
        ip_address = request.data.get('ip_address')
        if not ip_address:
            return Response({"error": "ip_address parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        axes_reset(ip=ip_address)
        AdminAuditService.log_event(
            event_type='IP_UNBLOCKED',
            actor=request.user.username,
            target_user=None,
            ip_address=ip_address,
            details=f"IP address '{ip_address}' manually unblocked by admin '{request.user.username}'."
        )
        return Response(
            {"message": f"IP address '{ip_address}' unblocked successfully."},
            status=status.HTTP_200_OK
        )


