from rest_framework import serializers
from datetime import timedelta

import pytz
from django.utils import timezone

from authentication.models import Company
from tent.models import Tent
from camera.models import Camera, CameraHeartbeat, KitchenViolationReport
from .models import DeviceActivityLog, OrangePiDevice

RIYADH_TZ = pytz.timezone("Asia/Riyadh")

# Camera list: online if CameraHeartbeat.updated_at (fallback: .time) is within this window.
CAMERA_HEARTBEAT_ONLINE_WINDOW = timedelta(minutes=5)


class TentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tent
        fields = ['id', 'name', 'is_arafa', 'capacity']


class CompanyWithTentsSerializer(serializers.ModelSerializer):
    tents = TentBriefSerializer(many=True, read_only=True, source='tent')
    tent_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'name_ar', 'tent_count', 'tents']

    def get_tent_count(self, obj):
        count = getattr(obj, '_tent_count', None)
        if count is not None:
            return count
        return obj.tent.count()


class OrangePiDeviceSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    last_seen_riyadh = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    tent_name = serializers.CharField(source='tent.name', read_only=True)

    class Meta:
        model = OrangePiDevice
        fields = [
            'id', 'name', 'device_id', 'mac_address', 'port',
            'company', 'company_name',
            'tent', 'tent_name',
            'last_seen_riyadh', 'is_online',
        ]

    def get_is_online(self, obj):
        return obj.online

    def get_last_seen_riyadh(self, obj):
        if not obj.last_seen:
            return None
        return obj.last_seen.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")


class CameraBriefSerializer(serializers.ModelSerializer):
    heart_beat_time = serializers.SerializerMethodField()
    tent_name       = serializers.CharField(source='tent.name', read_only=True, default=None)
    company_id      = serializers.IntegerField(source='tent.company.id', read_only=True, default=None)
    company_name    = serializers.CharField(source='tent.company.name', read_only=True, default=None)
    is_online       = serializers.SerializerMethodField()

    class Meta:
        model = Camera
        fields = (
            'id', 'sn', 'heart_beat_time', 'type', 'tent_id', 'tent_name',
            'company_id', 'company_name', 'is_online',
        )

    def _get_heartbeat_time(self, obj):
        """Prefer server-side last save (updated_at); else device-reported time."""
        hb = getattr(obj, 'heartbeat', None)
        if not hb:
            return None
        return hb.updated_at or hb.time

    def get_heart_beat_time(self, obj):
        ts = self._get_heartbeat_time(obj)
        if not ts:
            return None
        return ts.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def get_is_online(self, obj):
        ts = self._get_heartbeat_time(obj)
        if not ts:
            return False
        now_riyadh = timezone.now().astimezone(RIYADH_TZ)
        threshold = now_riyadh - CAMERA_HEARTBEAT_ONLINE_WINDOW
        return ts.astimezone(RIYADH_TZ) >= threshold


class CameraHeartbeatSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()

    class Meta:
        model = CameraHeartbeat
        fields = (
            'version', 'mac_address', 'ip_address', 'connection_type',
            'ip_address_method', 'host_name', 'time_zone', 'hw_platform',
            'report_date', 'time', 'status_log',
        )

    def get_time(self, obj):
        if not obj.time:
            return None
        return obj.time.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")


class CameraDetailSerializer(serializers.ModelSerializer):
    tent_name       = serializers.CharField(source='tent.name', read_only=True, default=None)
    heart_beat_time = serializers.SerializerMethodField()
    created_at      = serializers.SerializerMethodField()
    updated_at      = serializers.SerializerMethodField()
    heartbeat       = CameraHeartbeatSerializer(read_only=True)
    hls_url         = serializers.SerializerMethodField()
    is_livestream_active = serializers.SerializerMethodField()

    class Meta:
        model = Camera
        fields = (
            'id', 'sn', 'type', 'tent_id', 'tent_name',
            'video_link', 'heart_beat_time', 'created_at', 'updated_at',
            'heartbeat', 'hls_url', 'is_livestream_active',
        )

    def _fmt(self, dt):
        if not dt:
            return None
        return dt.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def get_heart_beat_time(self, obj):
        return self._fmt(obj.heart_beat_time)

    def get_created_at(self, obj):
        return self._fmt(obj.created_at)

    def get_updated_at(self, obj):
        return self._fmt(obj.updated_at)

    def get_hls_url(self, obj):
        ls = getattr(obj, 'livestream', None)
        return ls.hls_url if ls else None

    def get_is_livestream_active(self, obj):
        ls = getattr(obj, 'livestream', None)
        return ls.is_active if ls else None


class KitchenViolationSerializer(serializers.ModelSerializer):
    camera_sn  = serializers.CharField(source='camera.sn', read_only=True)
    tent_id    = serializers.IntegerField(source='camera.tent_id', read_only=True)
    tent_name  = serializers.CharField(source='camera.tent.name', read_only=True)
    start_time = serializers.SerializerMethodField()
    end_time   = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model  = KitchenViolationReport
        fields = (
            'id', 'camera_id', 'camera_sn', 'tent_id', 'tent_name',
            'violation', 'violation_list', 'annotator_status', 'current_status',
            'is_annotated', 'is_rejected', 'image',
            'start_time', 'end_time', 'created_at', 'updated_at',
        )

    def _fmt(self, dt):
        if not dt:
            return None
        return dt.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def get_start_time(self, obj):
        return self._fmt(obj.start_time)

    def get_end_time(self, obj):
        return self._fmt(obj.end_time)

    def get_created_at(self, obj):
        return self._fmt(obj.created_at)

    def get_updated_at(self, obj):
        return self._fmt(obj.updated_at)


class CameraDeliveryBucketSerializer(serializers.Serializer):
    bucket_start = serializers.CharField()
    bucket_end = serializers.CharField()
    actual_count = serializers.IntegerField()
    expected_count = serializers.IntegerField()
    missing_count = serializers.IntegerField()
    delivery_percent = serializers.FloatField()
    status = serializers.CharField()


class DeviceActivityLogSerializer(serializers.ModelSerializer):
    device_identifier = serializers.SerializerMethodField()
    device_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    tent_name = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = DeviceActivityLog
        fields = (
            'id', 'device_type', 'status', 'timestamp',
            'device_identifier', 'device_name',
            'company_name', 'tent_name',
            'details', 'created_at',
        )

    def _fmt(self, dt):
        if not dt:
            return None
        return dt.astimezone(RIYADH_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def get_timestamp(self, obj):
        return self._fmt(obj.timestamp)

    def get_created_at(self, obj):
        return self._fmt(obj.created_at)

    def _get_device(self, obj):
        if obj.device_type == 'camera':
            return obj.camera
        elif obj.device_type == 'orange_pi':
            return obj.orange_pi_device
        elif obj.device_type == 'access_point':
            return obj.access_point
        return None

    def get_device_identifier(self, obj):
        device = self._get_device(obj)
        if device is None:
            return None
        if obj.device_type == 'camera':
            return device.sn
        elif obj.device_type == 'orange_pi':
            return device.device_id
        elif obj.device_type == 'access_point':
            return device.SN
        return None

    def get_device_name(self, obj):
        device = self._get_device(obj)
        if device is None:
            return None
        if obj.device_type == 'camera':
            return device.sn
        elif obj.device_type == 'orange_pi':
            return device.name
        elif obj.device_type == 'access_point':
            return device.SN
        return None

    def get_company_name(self, obj):
        device = self._get_device(obj)
        if device is None:
            return None
        if obj.device_type == 'camera':
            return device.tent.company.name if device.tent and device.tent.company else None
        elif obj.device_type == 'orange_pi':
            return device.company.name if device.company else None
        return None

    def get_tent_name(self, obj):
        device = self._get_device(obj)
        if device is None:
            return None
        if obj.device_type == 'camera':
            return device.tent.name if device.tent else None
        elif obj.device_type == 'orange_pi':
            return device.tent.name if device.tent else None
        return None
