from rest_framework import serializers

class AccessVerifySerializer(serializers.Serializer):
    card_uid = serializers.CharField(max_length=50, required=True)
    device_id = serializers.CharField(max_length=50, required=True)
