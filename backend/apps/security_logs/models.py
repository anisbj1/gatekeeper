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
