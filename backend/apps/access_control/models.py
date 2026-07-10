from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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

class Schedule(models.Model):
    name = models.CharField(max_length=100)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        days = []
        if self.monday: days.append("Mon")
        if self.tuesday: days.append("Tue")
        if self.wednesday: days.append("Wed")
        if self.thursday: days.append("Thu")
        if self.friday: days.append("Fri")
        if self.saturday: days.append("Sat")
        if self.sunday: days.append("Sun")
        days_str = ", ".join(days) or "No days"
        return f"{self.name} ({days_str}: {self.start_time} - {self.end_time})"

class AccessRule(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, null=True, blank=True, related_name='access_rules')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='access_rules')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='access_rules')
    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_rules')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if not self.card and not self.user:
            raise ValidationError("An AccessRule must be linked to either a Card or a User.")
        if self.card and self.user:
            raise ValidationError("An AccessRule cannot be linked to both a Card and a User. Select only one.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.card.uid if self.card else f"User {self.user.username}"
        sched = self.schedule.name if self.schedule else "24/7"
        return f"Rule: {target} -> {self.device.name} ({sched})"

