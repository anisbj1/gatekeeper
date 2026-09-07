from .models import AccessLog, AdminAuditLog

class AuditLoggingService:
    @classmethod
    def create_log(cls, card_uid: str, device_id: str, authorized: bool, user_details: str) -> AccessLog:
        return AccessLog.objects.create(
            card_uid=card_uid,
            device_id=device_id,
            authorized=authorized,
            user_details=user_details
        )


class AdminAuditService:
    @classmethod
    def log_event(cls, event_type: str, actor: str = None, target_user: str = None, ip_address: str = None, details: str = "") -> AdminAuditLog:
        return AdminAuditLog.objects.create(
            event_type=event_type,
            actor=actor,
            target_user=target_user,
            ip_address=ip_address,
            details=details
        )

