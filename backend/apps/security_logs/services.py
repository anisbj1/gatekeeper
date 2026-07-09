from .models import AccessLog

class AuditLoggingService:
    @classmethod
    def create_log(cls, card_uid: str, device_id: str, authorized: bool, user_details: str) -> AccessLog:
        return AccessLog.objects.create(
            card_uid=card_uid,
            device_id=device_id,
            authorized=authorized,
            user_details=user_details
        )
