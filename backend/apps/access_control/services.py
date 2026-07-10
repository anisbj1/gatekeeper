from .models import Device, Card, AccessRule
from apps.security_logs.services import AuditLoggingService
from django.db.models import Q
from django.utils import timezone

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

        # 2. Access Rule check
        rules = AccessRule.objects.filter(
            device=device,
            is_active=True
        ).filter(
            Q(card=card) | Q(user=card.user)
        )

        if not rules.exists():
            cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"No Access Rule ({card.user.username})")
            return {"authorized": False, "message": "No Access Rule", "action": "keep_locked"}

        # 3 & 4. Date Window & Schedule checks
        local_now = timezone.localtime(timezone.now())
        current_date = local_now.date()
        current_time = local_now.time()
        current_day = local_now.isoweekday()  # 1 (Monday) to 7 (Sunday)

        has_date_valid_rule_but_schedule_restricted = False

        for rule in rules:
            # Check Date Window
            date_valid = True
            if rule.start_date and current_date < rule.start_date:
                date_valid = False
            if rule.end_date and current_date > rule.end_date:
                date_valid = False

            if not date_valid:
                continue

            # Check Schedule
            schedule_valid = True
            if rule.schedule:
                if rule.schedule.day_of_week != current_day:
                    schedule_valid = False
                elif not (rule.schedule.start_time <= current_time <= rule.schedule.end_time):
                    schedule_valid = False

            if not schedule_valid:
                has_date_valid_rule_but_schedule_restricted = True
                continue

            # Fully authorized rule found!
            username = card.user.get_full_name() or card.user.username
            cls._log_attempt(card_uid, device_id, authorized=True, user_details=username)
            return {
                "authorized": True,
                "message": f"Welcome, {username}",
                "action": "unlock"
            }

        # If we reach here, none of the active rules allowed access
        if has_date_valid_rule_but_schedule_restricted:
            cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"Schedule Restricted ({card.user.username})")
            return {"authorized": False, "message": "Schedule Restricted", "action": "keep_locked"}
        else:
            cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"Date Exceeded ({card.user.username})")
            return {"authorized": False, "message": "Date Exceeded", "action": "keep_locked"}

    @classmethod
    def _log_attempt(cls, card_uid: str, device_id: str, authorized: bool, user_details: str):
        AuditLoggingService.create_log(
            card_uid=card_uid,
            device_id=device_id,
            authorized=authorized,
            user_details=user_details
        )

