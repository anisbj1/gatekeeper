from django.db import models
from django.contrib.auth.models import User

class Device(models.Model):
    device_id = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class Card(models.Model):
    uid = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rfid_cards')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Standardize UID formatting (strip colons/spaces, convert to uppercase)
        if self.uid:
            self.uid = self.uid.replace(':', '').replace(' ', '').upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Card {self.uid} - {self.user.username}"
