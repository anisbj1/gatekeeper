from django.db import models

class AccessLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    device_id = models.CharField(max_length=50, db_index=True)
    card_uid = models.CharField(max_length=50, db_index=True)
    authorized = models.BooleanField()
    user_details = models.CharField(max_length=200)

    def __str__(self):
        status_str = "GRANTED" if self.authorized else "DENIED"
        return f"[{self.timestamp}] Device {self.device_id} - Card {self.card_uid} ({status_str})"


class AdminAuditLog(models.Model):
    EVENT_TYPES = [
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('PASSWORD_CHANGED', 'Password Changed'),
        ('ROLE_CHANGED', 'Role / Permissions Changed'),
        ('IP_BLOCKED', 'IP Address Blocked'),
        ('IP_UNBLOCKED', 'IP Address Unblocked'),
        ('SESSION_EXPIRED', 'Session Expired (Inactivity / Max Age)'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    actor = models.CharField(max_length=150, blank=True, null=True)
    target_user = models.CharField(max_length=150, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.event_type} - Actor: {self.actor or 'System'} - IP: {self.ip_address}"

