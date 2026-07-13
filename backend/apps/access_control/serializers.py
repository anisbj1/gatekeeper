import re
from rest_framework import serializers

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

