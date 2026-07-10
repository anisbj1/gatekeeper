from django.contrib import admin
from .models import Device, Card, Schedule, AccessRule

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('device_id', 'name')

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('uid', 'user', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('uid', 'user__username')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('name', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'start_time', 'end_time')
    search_fields = ('name',)


@admin.register(AccessRule)
class AccessRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'card', 'device', 'schedule', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'device', 'schedule')
    search_fields = ('user__username', 'card__uid', 'device__name', 'schedule__name')

