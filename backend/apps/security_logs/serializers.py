from rest_framework import serializers
from .models import AccessLog

class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = ['id', 'timestamp', 'device_id', 'card_uid', 'authorized', 'user_details']
        read_only_fields = ['id', 'timestamp']
