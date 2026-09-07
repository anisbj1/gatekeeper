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
                day_fields = {
                    1: 'monday',
                    2: 'tuesday',
                    3: 'wednesday',
                    4: 'thursday',
                    5: 'friday',
                    6: 'saturday',
                    7: 'sunday'
                }
                day_field = day_fields.get(current_day)
                if not getattr(rule.schedule, day_field, False):
                    schedule_valid = False
                elif not (rule.schedule.start_time <= current_time <= rule.schedule.end_time):
                    schedule_valid = False

            if not schedule_valid:
                has_date_valid_rule_but_schedule_restricted = True
                continue

            # Fully authorized rule found!
            has_biometrics = False
            try:
                if hasattr(card.user, 'face_profile') and card.user.face_profile.is_biometric_active:
                    has_biometrics = True
            except Exception:
                pass

            if has_biometrics:
                from apps.face_recognition.web_services import BiometricCameraVerificationService
                # Trigger local webcam face recognition automatically
                face_matched = BiometricCameraVerificationService.verify_face_from_webcam(
                    user=card.user,
                    device=device,
                    card=card
                )
                if not face_matched:
                    cls._log_attempt(card_uid, device_id, authorized=False, user_details=f"Face ID Failed ({card.user.username})")
                    return {
                        "authorized": False,
                        "message": "Face ID Failed",
                        "action": "keep_locked"
                    }

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


class UserSessionService:
    @classmethod
    def invalidate_user_sessions(cls, user_id: int):
        """
        Invalidates all active database sessions belonging to a specific user.
        """
        from django.contrib.sessions.models import Session
        user_id_str = str(user_id)
        sessions_to_delete = []
        for s in Session.objects.all():
            try:
                decoded = s.get_decoded()
                if str(decoded.get('_auth_user_id')) == user_id_str:
                    sessions_to_delete.append(s.pk)
            except Exception:
                continue
        if sessions_to_delete:
            Session.objects.filter(pk__in=sessions_to_delete).delete()


