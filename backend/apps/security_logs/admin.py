from django.contrib import admin
from django.contrib.admin.models import LogEntry
from .models import AccessLog

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'device_id', 'card_uid', 'authorized', 'user_details')
    list_filter = ('authorized', 'device_id')
    search_fields = ('card_uid', 'user_details')


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'action_type', 'object_repr', 'change_message')
    search_fields = ('user__username', 'object_repr', 'change_message')
    list_filter = ('action_time', 'action_flag')

    def action_type(self, obj):
        if obj.is_addition():
            return "Addition"
        elif obj.is_change():
            return "Change"
        elif obj.is_deletion():
            return "Deletion"
        return "Unknown"

    action_type.short_description = 'Action Type'
    action_type.admin_order_field = 'action_flag'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

