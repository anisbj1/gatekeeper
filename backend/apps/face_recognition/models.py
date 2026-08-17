import uuid
from django.db import models
from django.contrib.auth.models import User
from apps.access_control.models import Device, Card

class FaceProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='face_profile')
    is_biometric_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status_str = "Active" if self.is_biometric_active else "Inactive"
        return f"{self.user.username} Biometric Profile ({status_str})"

class FaceImage(models.Model):
    profile = models.ForeignKey(FaceProfile, on_delete=models.CASCADE, related_name='images')
    original_image = models.ImageField(upload_to='biometrics/originals/%Y/%m/%d/')
    cropped_image = models.ImageField(upload_to='biometrics/faces/%Y/%m/%d/')
    is_reference = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        ref_str = " [Ref]" if self.is_reference else ""
        return f"Image for {self.profile.user.username} ({self.id}){ref_str}"

class FaceEmbedding(models.Model):
    profile = models.ForeignKey(FaceProfile, on_delete=models.CASCADE, related_name='embeddings')
    embedding = models.JSONField()  # Stores array of 512 floats
    model_version = models.CharField(max_length=50, default='facenet_v1')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Embedding for {self.profile.user.username} ({self.model_version})"

class EnrollmentSession(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COLLECTING', 'Collecting'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollment_sessions')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='enrollment_sessions')
    status = models.CharField(max_length=20, default='PENDING', choices=STATUS_CHOICES)
    images_required = models.IntegerField(default=5)
    images_collected = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Session {self.id} - {self.user.username} ({self.status})"

class RecognitionAttempt(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recognition_attempts')
    card = models.ForeignKey(Card, on_delete=models.SET_NULL, null=True, blank=True, related_name='recognition_attempts')
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='recognition_attempts')
    captured_image = models.ImageField(upload_to='biometrics/attempts/%Y/%m/%d/', null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    authorized = models.BooleanField()
    error_message = models.CharField(max_length=200, null=True, blank=True)
    processing_time_ms = models.IntegerField()

    def __str__(self):
        status_str = "GRANTED" if self.authorized else "DENIED"
        user_str = self.user.username if self.user else "Unknown"
        return f"[{self.timestamp}] Device {self.device.device_id} - User {user_str} ({status_str}, conf={self.confidence_score})"
