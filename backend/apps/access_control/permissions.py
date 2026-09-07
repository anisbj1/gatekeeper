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


class IsSuperAdminUser(permissions.BasePermission):
    """
    Permission checking that the requesting user is authenticated and is a Super Administrator (is_superuser=True).
    """
    message = "Action restricted to Super Administrators."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.is_superuser)


class IsOperationalAdminUser(permissions.BasePermission):
    """
    Permission checking that the requesting user is authenticated and is a staff member (is_staff=True).
    """
    message = "Action restricted to operational staff."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff)


class CanManageUsersPermission(permissions.BasePermission):
    """
    Operational staff can view users (GET).
    Creating, updating, deleting, or locking/unlocking accounts requires explicit permission or SuperAdmin.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff):
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Write actions: superuser or has model permissions
        if request.user.is_superuser:
            return True
            
        if request.method == 'POST':
            return request.user.has_perm('auth.add_user')
        if request.method in ['PUT', 'PATCH']:
            return request.user.has_perm('auth.change_user')
        if request.method == 'DELETE':
            return request.user.has_perm('auth.delete_user')
            
        return False


class CanManageDevicesPermission(permissions.BasePermission):
    """
    Operational staff can view devices (GET).
    Modifying device hardware registrations or API tokens is restricted to SuperAdmin or specific permission.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff):
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return True
            
        return bool(request.user.is_superuser or request.user.has_perm('access_control.change_device'))


class CanViewAdminAuditLogsPermission(permissions.BasePermission):
    """
    Admin audit logs are sensitive and only viewable by SuperAdmin or security auditor role.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff):
            return False
            
        return bool(request.user.is_superuser or request.user.has_perm('security_logs.view_adminauditlog'))

