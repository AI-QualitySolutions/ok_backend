from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
import pytz

from .models import DeviceActivityLog, OrangePiDevice

RIYADH_TZ = pytz.timezone("Asia/Riyadh")


@admin.register(OrangePiDevice)
class OrangePiDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_id', 'mac_address', 'company', 'tent', 'port', 'last_seen', 'get_is_online']
    list_filter = ['company', 'tent']
    search_fields = ['name', 'device_id', 'mac_address']
    readonly_fields = ['last_seen', 'created_at', 'updated_at']
    ordering = ['company', 'tent']

    fieldsets = (
        ('Device Info', {
            'fields': ('name', 'device_id', 'mac_address', 'port')
        }),
        ('Assignment', {
            'fields': ('company', 'tent')
        }),
        ('Timestamps', {
            'fields': ('last_seen', 'created_at', 'updated_at')
        }),
    )

    @admin.display(boolean=True, description='Online')
    def get_is_online(self, obj):
        if not obj.last_seen:
            return False
        threshold = timezone.now().astimezone(RIYADH_TZ) - timedelta(minutes=1)
        return obj.last_seen.astimezone(RIYADH_TZ) >= threshold


@admin.register(DeviceActivityLog)
class DeviceActivityLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'device_type', 'status', 'timestamp', 'get_device_identifier']
    list_filter = ['device_type', 'status', 'timestamp']
    search_fields = [
        'camera__sn',
        'orange_pi_device__device_id',
        'orange_pi_device__mac_address',
        'access_point__SN',
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-timestamp']

    @admin.display(description='Device Identifier')
    def get_device_identifier(self, obj):
        if obj.device_type == 'camera' and obj.camera:
            return obj.camera.sn
        elif obj.device_type == 'orange_pi' and obj.orange_pi_device:
            return obj.orange_pi_device.device_id
        elif obj.device_type == 'access_point' and obj.access_point:
            return obj.access_point.SN
        return '-'