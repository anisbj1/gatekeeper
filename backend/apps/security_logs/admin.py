from django.contrib import admin
from .models import AccessLog

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device_id', 'card_uid', 'authorized', 'user_details')
    list_filter = ('authorized', 'device_id')
    search_fields = ('card_uid', 'user_details')
