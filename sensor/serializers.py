from rest_framework import serializers
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord, SensorLocation
from django.db.models import Func, Avg, Min, Max, F
from django.utils.timezone import localtime
from django.utils.timezone import localtime, now
from datetime import timedelta

class SensorLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorLocation
        fields = ("id", "name")

class EnvironmentSensorSerializer(serializers.ModelSerializer):
    tent_name = serializers.SerializerMethodField(read_only=True)
    indicator = serializers.SerializerMethodField(read_only=True)
    map_temp = serializers.SerializerMethodField()
    class Meta:
        model = EnvironmentSensor
        fields = ("id" ,"tent", "tent_name", "sn", "name", "ip", "lat", "long",
                  "location", "top", "left", "online", "tempareture", "humidity",
                  "last_entry_time", "type", "indicator", "map_temp")
        read_only_fields = ("id", "tent_name")

    def get_tent_name(self, obj):
        return obj.tent.name if obj.tent else None

    def get_map_temp(self, obj):
        return obj.tempareture

    def get_indicator(self, obj):
        if obj.tempareture:
            if obj.tempareture > 38:
                return "red"
            else:
                return "green"
        return None
class EnvironmentSensorAverageSerializer(serializers.ModelSerializer):
    tent_name = serializers.SerializerMethodField(read_only=True)
    indicator = serializers.SerializerMethodField(read_only=True)
    map_temp = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = EnvironmentSensor
        fields = ("id" ,"tent", "tent_name", "sn", "name", "ip", "lat", "long",
                  "location", "top", "left", "online", "tempareture", "humidity",
                  "last_entry_time", "type", "indicator", "map_temp")
        read_only_fields = ("id", "tent_name")

    def get_tent_name(self, obj):
        return obj.tent.name if obj.tent else None

    def get_map_temp(self, obj):
        return obj.tempareture

    def get_indicator(self, obj):
        if obj.tempareture:
            if obj.tempareture > 38:
                return "red"
            else:
                return "green"
        return None
    def get_online(self, obj):
        if obj.last_entry_time:
            last_entry_time = localtime(obj.last_entry_time)
            current_time = localtime(now())
            if current_time - last_entry_time <= timedelta(minutes=30):
                return True
        return False
class DateWiseEnvironmentSensorSerializer(serializers.ModelSerializer):
    tent_name = serializers.SerializerMethodField(read_only=True)
    indicator = serializers.SerializerMethodField(read_only=True)
    tempareture = serializers.SerializerMethodField(read_only=True)
    humidity = serializers.SerializerMethodField(read_only=True)
    last_entry_time = serializers.SerializerMethodField(read_only=True)
    map_temp = serializers.SerializerMethodField(read_only=True)
    online = serializers.SerializerMethodField(read_only=True)
    

    class Meta:
        model = EnvironmentSensor
        fields = ("id" ,"tent", "tent_name", "sn", "name", "ip", "lat", "long",
                  "location", "top", "left", "online", "tempareture", "humidity",
                  "last_entry_time", "type", "indicator", "map_temp")
        read_only_fields = ("id", "tent_name")

    def get_tent_name(self, obj):
        return obj.tent.name if obj.tent else None

    def get_map_temp(self, obj):
        start = self.context.get('start_date_time')
        end = self.context.get('end_date_time')

        if not (start and end):
            return None
        avg_temp = EnvironmentSensorRecord.objects.filter(
            sensor=obj,
            created_at__range=(start, end)
        ).aggregate(avg=Avg('tempareture'))['avg']
        return round(avg_temp, 2) if avg_temp is not None else None


    def _get_last_record(self, obj):
        cached = getattr(obj, '_cached_last_record', sentinel := object())
        if cached is not sentinel:
            return cached

        start = self.context.get('start_date_time')
        end = self.context.get('end_date_time')
        if not (start and end):
            obj._cached_last_record = None
            return None
        record = EnvironmentSensorRecord.objects.filter(
            sensor=obj,
            created_at__range=(start, end)
        ).order_by('-created_at').first()
        obj._cached_last_record = record
        return record

    def get_tempareture(self, obj):
        record = self._get_last_record(obj)
        return round(record.tempareture, 2) if record else None

    def get_humidity(self, obj):
        record = self._get_last_record(obj)
        return record.humidity if record else None

    def get_indicator(self, obj):
        record = self._get_last_record(obj)
        if record:
            return "red" if record.tempareture > 38 else "green"
        return None

    def get_last_entry_time(self, obj):
        record = self._get_last_record(obj)
        if record and record.created_at:
            return localtime(record.created_at).strftime('%Y-%m-%d %H:%M:%S')
        return None
    def get_online(self, obj):
        record = self._get_last_record(obj)
        if record and record.created_at:
            last_entry_time = localtime(record.last_entry_time)
            current_time = localtime(now())
            if current_time - last_entry_time <= timedelta(minutes=30):
                return True
            else:
                return False
        return False

class NestedEnvironmentSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentSensor
        fields = ("id", "sn", "name")


class EnvironmentSensorRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentSensorRecord
        fields = ('sensor', 'temperature', 'humidity', 'last_entry_time', 'start_time', 'end_time', 'created_at', 'updated_at')