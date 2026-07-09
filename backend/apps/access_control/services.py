from .models import Device, Card
from apps.security_logs.services import AuditLoggingService

class AccessValidationService:
    @classmethod
    def validate_scan(cls, card_uid: str, device_id: str) -> dict:
        try:
            device = Device.objects.get(device_id=device_id)
            if not device.is_active:
                cls._log_attempt(card_uid, device_id, authorized=False, user_details="Device Inactive")
                return {"authorized": False, "message": "Device Inactive", "action": "keep_locked"}
        except Device.DoesNotExist:
            cls._log_attempt(card_uid, device_id, authorized=False, user_details="Unknown Device")
            return {"authorized": False, "message": "Unknown Device", "action": "keep_locked"}

        try:
            card = Card.objects.select_related('user').get(uid=card_uid)
            if not card.is_active:
                cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"Blocked Card ({card.user.username})")
                return {"authorized": False, "message": "Card Blocked", "action": "keep_locked"}
            
            if not card.user.is_active:
                cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"Inactive User ({card.user.username})")
                return {"authorized": False, "message": "User Inactive", "action": "keep_locked"}
        except Card.DoesNotExist:
            cls._log_attempt(card_uid, device_id, authorized=False, user_details="Unknown Card")
            return {"authorized": False, "message": "Access Denied", "action": "keep_locked"}

        username = card.user.get_full_name() or card.user.username
        cls._log_attempt(card_uid, device_id, authorized=True, user_details=username)
        return {
            "authorized": True,
            "message": f"Welcome, {username}",
            "action": "unlock"
        }

    @classmethod
    def _log_attempt(cls, card_uid: str, device_id: str, authorized: bool, user_details: str):
        AuditLoggingService.create_log(
            card_uid=card_uid,
            device_id=device_id,
            authorized=authorized,
            user_details=user_details
        )
