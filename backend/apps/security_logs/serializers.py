from rest_framework import serializers
from .models import AccessLog, AdminAuditLog

class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = ['id', 'timestamp', 'device_id', 'card_uid', 'authorized', 'user_details']
        read_only_fields = ['id', 'timestamp']


class AdminAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminAuditLog
        fields = ['id', 'timestamp', 'event_type', 'actor', 'target_user', 'ip_address', 'details']
        read_only_fields = ['id', 'timestamp']

