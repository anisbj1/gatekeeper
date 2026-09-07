from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from .models import AccessLog, AdminAuditLog
from .serializers import AccessLogSerializer, AdminAuditLogSerializer
from apps.access_control.permissions import CanViewAdminAuditLogsPermission

class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    queryset = AccessLog.objects.all().order_by('-timestamp')
    serializer_class = AccessLogSerializer

    def get_queryset(self):
        queryset = AccessLog.objects.all().order_by('-timestamp')
        
        device_id = self.request.query_params.get('device')
        if device_id:
            queryset = queryset.filter(device_id__icontains=device_id)
            
        card_uid = self.request.query_params.get('card_uid')
        if card_uid:
            queryset = queryset.filter(card_uid__icontains=card_uid)
            
        authorized = self.request.query_params.get('authorized')
        if authorized is not None:
            queryset = queryset.filter(authorized=authorized.lower() == 'true')
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user_details__icontains=search) |
                Q(device_id__icontains=search) |
                Q(card_uid__icontains=search)
            )
            
        return queryset


class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [CanViewAdminAuditLogsPermission]
    queryset = AdminAuditLog.objects.all().order_by('-timestamp')
    serializer_class = AdminAuditLogSerializer

    def get_queryset(self):
        queryset = AdminAuditLog.objects.all().order_by('-timestamp')
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        actor = self.request.query_params.get('actor')
        if actor:
            queryset = queryset.filter(actor__icontains=actor)
        target = self.request.query_params.get('target')
        if target:
            queryset = queryset.filter(target_user__icontains=target)
        return queryset

