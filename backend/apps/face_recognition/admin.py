from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import FaceProfile, FaceImage, FaceEmbedding, EnrollmentSession, RecognitionAttempt

class FaceImageInline(admin.TabularInline):
    model = FaceImage
    extra = 0
    readonly_fields = ('cropped_preview', 'original_preview')

    def cropped_preview(self, obj):
        if obj.cropped_image:
            return mark_safe(f'<img src="{obj.cropped_image.url}" style="width: 80px; height: 80px; object-fit: cover; border: 1px solid #ccc; border-radius: 4px;" />')
        return "No Cropped Image"
    cropped_preview.short_description = 'Cropped Face'

    def original_preview(self, obj):
        if obj.original_image:
            return mark_safe(f'<img src="{obj.original_image.url}" style="height: 80px; object-fit: contain; border: 1px solid #ccc; border-radius: 4px;" />')
        return "No Original Image"
    original_preview.short_description = 'Original Capture'


class FaceEmbeddingInline(admin.TabularInline):
    model = FaceEmbedding
    extra = 0
    readonly_fields = ('model_version', 'embedding_snippet', 'created_at')
    exclude = ('embedding',)

    def embedding_snippet(self, obj):
        if obj.embedding:
            snippet = str(obj.embedding[:5]) + "..."
            return f"512-dim Vector: {snippet}"
        return "None"
    embedding_snippet.short_description = 'Embedding Vector'


@admin.register(FaceProfile)
class FaceProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_biometric_active', 'reference_image_preview', 'embeddings_count', 'created_at', 'updated_at')
    list_filter = ('is_biometric_active',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    inlines = [FaceImageInline, FaceEmbeddingInline]

    def reference_image_preview(self, obj):
        ref_image = obj.images.filter(is_reference=True).first()
        if ref_image and ref_image.cropped_image:
            return mark_safe(f'<img src="{ref_image.cropped_image.url}" style="width: 45px; height: 45px; border-radius: 50%; object-fit: cover; border: 2px solid #555;" />')
        return mark_safe('<span style="color: red; font-weight: bold;">No Ref Image</span>')
    reference_image_preview.short_description = 'Reference Photo'

    def embeddings_count(self, obj):
        return obj.embeddings.count()
    embeddings_count.short_description = 'Templates Count'


@admin.register(EnrollmentSession)
class EnrollmentSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'device', 'status', 'progress', 'created_at', 'expires_at')
    list_filter = ('status', 'device')
    search_fields = ('user__username', 'id')
    readonly_fields = ('created_at',)

    def progress(self, obj):
        return f"{obj.images_collected} / {obj.images_required}"
    progress.short_description = 'Progress (Collected/Req)'


@admin.register(RecognitionAttempt)
class RecognitionAttemptAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device_lbl', 'user_lbl', 'card_lbl', 'authorized_badge', 'confidence_score', 'processing_time_ms', 'captured_image_thumbnail')
    list_filter = ('authorized', 'device', 'timestamp')
    search_fields = ('user__username', 'card__uid', 'error_message', 'device__device_id')
    readonly_fields = (
        'timestamp', 'user', 'card', 'device', 'captured_image', 
        'confidence_score', 'authorized', 'error_message', 
        'processing_time_ms', 'detailed_image_preview'
    )
    exclude = ('captured_image',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # We allow deletion of audit logs if needed, but not modification.
        return True

    def device_lbl(self, obj):
        return obj.device.device_id
    device_lbl.short_description = 'Device'

    def user_lbl(self, obj):
        return obj.user.username if obj.user else "Unknown User"
    user_lbl.short_description = 'User'

    def card_lbl(self, obj):
        return obj.card.uid if obj.card else "No Card"
    card_lbl.short_description = 'Card'

    def authorized_badge(self, obj):
        if obj.authorized:
            return mark_safe('<span style="color: green; font-weight: bold; background-color: #e2fcd4; padding: 3px 8px; border-radius: 4px;">GRANTED</span>')
        else:
            return mark_safe(f'<span style="color: red; font-weight: bold; background-color: #fce4e4; padding: 3px 8px; border-radius: 4px;">DENIED</span>')
    authorized_badge.short_description = 'Status'

    def captured_image_thumbnail(self, obj):
        if obj.captured_image:
            return mark_safe(f'<img src="{obj.captured_image.url}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 4px;" />')
        return "No Photo"
    captured_image_thumbnail.short_description = 'Photo'

    def detailed_image_preview(self, obj):
        if obj.captured_image:
            return mark_safe(f'<img src="{obj.captured_image.url}" style="max-width: 400px; border-radius: 8px; border: 1px solid #ccc;" />')
        return "No image captured for this attempt"
    detailed_image_preview.short_description = 'Verification Frame'
