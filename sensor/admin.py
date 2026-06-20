from django.contrib import admin
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord, SensorLocation

# Register your models here.
# admin.site.register(EnvironmentSensor)


@admin.register(EnvironmentSensor)
class EnvironmentSensorAdmin(admin.ModelAdmin):
    search_fields = ['id',                   # sensor_id if using the model's primary key
                     'sn',
                     'tent__id',             # tent_id
                     'tent__company__id',
                     'tent__company__name', 'name', 'type']
    list_display = ['id', 'sn', 'name', "tent",
                    'tempareture', 'humidity', 'type', 'online']
    list_filter = ['type', "tent__company", 'online', 'check_neighbour', 'tent']


@admin.register(EnvironmentSensorRecord)
class EnvironmentSensorRecordAdmin(admin.ModelAdmin):
    search_fields = ['sensor__sn', 'sensor__name', 'sensor__tent__company__id', 'sensor__tent__company__name', 'id']
    list_display = ['id', 'sensor', 'tempareture',
                    'humidity', 'last_entry_time', 'created_at']
    list_filter = ['created_at', "sensor__tent__company", 'update_from_neighbour', 'sensor__tent__is_arafa', 'sensor']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sensor":
            kwargs["queryset"] = EnvironmentSensor.objects.filter(type="environment")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(SensorLocation)
class SensorLocationAdmin(admin.ModelAdmin):
    search_fields = ['id', 'name']
    list_display = ['id', 'name']
