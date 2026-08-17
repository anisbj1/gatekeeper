from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser, AllowAny
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
from .services import AccessValidationService
from .permissions import HasValidDeviceToken
from apps.security_logs.models import AccessLog
from apps.face_recognition.models import FaceProfile

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
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                return Response({"error": "User account is disabled"}, status=status.HTTP_403_FORBIDDEN)
            if not user.is_staff:
                return Response({"error": "Access restricted to staff members"}, status=status.HTTP_403_FORBIDDEN)
            
            login(request, user)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)


class AuthLogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


class AuthStatusView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DashboardStatsView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        today = timezone.localtime(timezone.now()).date()
        
        # Access log counts
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
    permission_classes = [IsAdminUser]
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
        return queryset


class CardViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
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
    permission_classes = [IsAdminUser]
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

