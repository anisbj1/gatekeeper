import re
from rest_framework import serializers
from apps.access_control.serializers import AccessVerifySerializer

class EnrollmentStartSerializer(AccessVerifySerializer):
    pass

class EnrollmentUploadSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=True)
    image = serializers.ImageField(required=True)
    device_id = serializers.CharField(max_length=50, required=True)

    def validate_device_id(self, value):
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError("Device ID must contain only letters, numbers, underscores, or hyphens.")
        return value

class BiometricVerifySerializer(AccessVerifySerializer):
    image = serializers.ImageField(required=True)


from django.contrib.auth.models import User
from .models import RecognitionAttempt, FaceProfile

class RecognitionAttemptSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    card_uid = serializers.SerializerMethodField()
    device_id_code = serializers.SerializerMethodField()

    class Meta:
        model = RecognitionAttempt
        fields = [
            'id', 'timestamp', 'user', 'username', 'card', 'card_uid', 
            'device', 'device_id_code', 'captured_image', 
            'confidence_score', 'authorized', 'error_message', 'processing_time_ms'
        ]
        read_only_fields = ['id', 'timestamp', 'captured_image']

    def get_username(self, obj):
        return obj.user.username if obj.user else "Unknown"

    def get_card_uid(self, obj):
        return obj.card.uid if obj.card else None

    def get_device_id_code(self, obj):
        return obj.device.device_id


class FaceProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    images_count = serializers.SerializerMethodField()

    class Meta:
        model = FaceProfile
        fields = ['id', 'user', 'username', 'is_biometric_active', 'created_at', 'updated_at', 'images_count']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username

    def get_images_count(self, obj):
        return obj.images.count()

