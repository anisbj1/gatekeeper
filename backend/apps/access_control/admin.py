from django.contrib import admin
from .models import Device, Card

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
