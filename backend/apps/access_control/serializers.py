import re
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Device, Card, Schedule, AccessRule

class AccessVerifySerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=50, required=True)
    device_id = serializers.CharField(max_length=50, required=True)

    def validate_card_uid(self, value):
        # Standardize formatting: uppercase, no spaces, no colons
        cleaned_uid = value.replace(':', '').replace(' ', '').upper()
        if not cleaned_uid:
            raise serializers.ValidationError("Card UID cannot be empty.")
        if not re.match(r'^[0-9A-F]{8,32}$', cleaned_uid):
            raise serializers.ValidationError("Card UID must be a valid hexadecimal string of length 8 to 32 characters (4 to 16 bytes).")
        return cleaned_uid

    def validate_device_id(self, value):
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError("Device ID must contain only letters, numbers, underscores, or hyphens.")
        return value


class UserSerializer(serializers.ModelSerializer):
    face_enrolled = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'roles', 'face_enrolled', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def get_face_enrolled(self, obj):
        try:
            return hasattr(obj, 'face_profile') and obj.face_profile.is_biometric_active
        except Exception:
            return False

    def get_roles(self, obj):
        return list(obj.groups.values_list('name', flat=True))



class CardSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = ['id', 'uid', 'user', 'user_details', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_details(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'device_id', 'name', 'api_token', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'api_token', 'created_at', 'updated_at']


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['id', 'name', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_time', 'end_time']
        read_only_fields = ['id']


class AccessRuleSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    card_uid = serializers.SerializerMethodField()
    device_name = serializers.SerializerMethodField()
    schedule_name = serializers.SerializerMethodField()

    class Meta:
        model = AccessRule
        fields = [
            'id', 'card', 'user', 'user_details', 'card_uid', 
            'device', 'device_name', 'schedule', 'schedule_name', 
            'start_date', 'end_date', 'is_active'
        ]
        read_only_fields = ['id']

    def get_user_details(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name} ({obj.user.username})"
        return None

    def get_card_uid(self, obj):
        if obj.card:
            return obj.card.uid
        return None

    def get_device_name(self, obj):
        return obj.device.name

    def get_schedule_name(self, obj):
        return obj.schedule.name if obj.schedule else "24/7"


