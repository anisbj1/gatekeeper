from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from .models import Device
from apps.security_logs.services import AuditLoggingService

class HasValidDeviceToken(permissions.BasePermission):
    message = "Invalid or missing device token."

    def has_permission(self, request, view):
        token = request.headers.get('X-Device-Token') or request.META.get('HTTP_X_DEVICE_TOKEN')
        
        # Get card_uid and device_id from request body (or headers/query params as fallback)
        device_id = None
        card_uid = None
        
        if isinstance(request.data, dict):
            device_id = request.data.get('device_id')
            card_uid = request.data.get('card_uid')
            
        if not device_id:
            device_id = request.headers.get('X-Device-Id') or request.META.get('HTTP_X_DEVICE_ID') or "UNKNOWN"
        if not card_uid:
            card_uid = request.headers.get('X-Card-Uid') or request.META.get('HTTP_X_CARD_UID') or "UNKNOWN"

        if not token:
            AuditLoggingService.create_log(
                card_uid=card_uid,
                device_id=device_id,
                authorized=False,
                user_details="Missing Device Token"
            )
            raise PermissionDenied("Authentication credentials were not provided.")

        if device_id == "UNKNOWN":
            AuditLoggingService.create_log(
                card_uid=card_uid,
                device_id=device_id,
                authorized=False,
                user_details="Missing Device ID"
            )
            raise PermissionDenied("Device ID is missing from request.")

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            AuditLoggingService.create_log(
                card_uid=card_uid,
                device_id=device_id,
                authorized=False,
                user_details="Unknown Device"
            )
            raise PermissionDenied("Device is not registered.")

        if device.api_token != token:
            AuditLoggingService.create_log(
                card_uid=card_uid,
                device_id=device_id,
                authorized=False,
                user_details="Invalid Device Token"
            )
            raise PermissionDenied("Invalid device token.")

        return True
