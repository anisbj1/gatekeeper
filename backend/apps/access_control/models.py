import secrets
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

def generate_api_token():
    return secrets.token_hex(32)

class Device(models.Model):
    device_id = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='Device ID must contain only letters, numbers, underscores, or hyphens.'
            )
        ]
    )
    name = models.CharField(max_length=100)
    api_token = models.CharField(max_length=64, unique=True, db_index=True, default=generate_api_token)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.name and self.name.strip() == "":
            raise ValidationError({'name': 'Name cannot contain only whitespace.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class Card(models.Model):
    uid = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9A-F]{8,32}$',
                message='Card UID must be a valid hexadecimal string of length 8 to 32 characters (4 to 16 bytes).'
            )
        ]
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rfid_cards')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean_fields(self, exclude=None):
        if self.uid:
            self.uid = self.uid.replace(':', '').replace(' ', '').upper()
        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        self.full_clean()
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

    def clean(self):
        super().clean()
        if self.name and self.name.strip() == "":
            raise ValidationError({'name': 'Name cannot contain only whitespace.'})
        
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({
                'end_time': 'End time must be strictly after start time.'
            })
            
        if not any([self.monday, self.tuesday, self.wednesday, self.thursday, self.friday, self.saturday, self.sunday]):
            raise ValidationError('At least one day of the week must be selected.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': "End date cannot be before start date."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.card.uid if self.card else f"User {self.user.username}"
        sched = self.schedule.name if self.schedule else "24/7"
        return f"Rule: {target} -> {self.device.name} ({sched})"

