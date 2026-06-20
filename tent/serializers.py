from rest_framework import serializers

from tent.models import Tent, TentsWaterTank, WaterTankSensorHistory, Country

from sensor.serializers import NestedEnvironmentSensorSerializer


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'name_ar']


class TentSerializer(serializers.ModelSerializer):
    environement_sensors = NestedEnvironmentSensorSerializer(
        many=True, read_only=True, source='sensors')
    map_image = serializers.SerializerMethodField()

    class Meta:
        model = Tent
        fields = (
            "id", "name", "longitude", "latitude", "location",
            "map_image", "created_by", "tent_image", "air_condition",
            "air_condition_update_time", "capacity", "is_arafa", "adjust",
            "fixed", "max_adjust_tempareture", "avg_adjust_tempareture",
            "min_adjust_tempareture", "is_adjust_tempareture", "max_adjust_humidity",
            "avg_adjust_humidity", "min_adjust_humidity", "is_adjust_humidity",
            "environement_sensors"
        )
        read_only_fields = ("id", "environement_sensors", "created_by")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.method == "POST":
            for field in ["name", "longitude", "latitude", "location", "capacity", "is_arafa"]:
                self.fields[field].required = True
        else:
            for field in ["name", "longitude", "latitude", "location", "capacity", "is_arafa"]:
                self.fields[field].required = False

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        validated_data["created_by"] = user
        validated_data["company"] = user.company  # Set the company from user

        return super().create(validated_data)

    def get_map_image(self, obj):
        request = self.context.get('request')
        if obj.map_image and hasattr(obj.map_image, 'url'):
            return request.build_absolute_uri(obj.map_image.url) if request else obj.map_image.url
        return None


class WaterSensorHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterTankSensorHistory
        fields = ("id", "water_sensor", "water_level",
                  "water_level_percent", "online", "start_time", "end_time")


class TentWaterTankSerializer(serializers.ModelSerializer):
    sensor_history = serializers.SerializerMethodField()

    class Meta:
        model = TentsWaterTank
        fields = ("id", "tent", "tank_number", "sensor_sn", "sensor_history")
        read_only_fields = ("id", "sensor_history")

    def validate(self, attrs):
        tent = attrs.get('tent')

        if not Tent.objects.filter(id=tent.id).exists():
            raise serializers.validationError(
                {"The selected tent does not exist."})
        return attrs

    def get_sensor_history(self, obj):
        prefetched = getattr(obj, '_prefetched_history', None)
        if prefetched is not None:
            latest_water_history = prefetched[0] if prefetched else None
        else:
            latest_water_history = WaterTankSensorHistory.objects.filter(
                water_sensor=obj).order_by('-end_time').first()
        return WaterSensorHistorySerializer(latest_water_history).data if latest_water_history else None


class WaterTankMonthlyDataSerializer(serializers.Serializer):
    tent_id = serializers.IntegerField()
    tent_name = serializers.CharField(max_length=255)
    tank_number = serializers.IntegerField()
    sensor_id = serializers.IntegerField()
    date_and_time = serializers.DateField()  # Assuming 'month' is a date object
    min_water_level_percent = serializers.FloatField()
    min_water_level_percent_date_and_time = serializers.DateTimeField(
        allow_null=True)  # Can be None
    max_water_level_percent = serializers.FloatField()
    max_water_level_percent_date_and_time = serializers.DateTimeField(
        allow_null=True)  # Can be None
    avg = serializers.FloatField()


# serializers.py

class CreateTentFromServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tent
        fields = ['company', 'name', 'map_image', 'capacity', 'is_arafa']
