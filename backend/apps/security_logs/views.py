from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from .models import AccessLog
from .serializers import AccessLogSerializer

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
