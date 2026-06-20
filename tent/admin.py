from django.contrib import admin
from tent.models import Tent, TentAirQualityRecord, TentsWaterTank, WaterTankSensorHistory, Country, TentGate


@admin.register(Tent)
class TentAdmin(admin.ModelAdmin):
    search_fields = ['name', 'company__name']
    list_display = ['id', 'name', 'location', 'is_arafa', 'company']
    list_filter = ['is_arafa', 'company__name']

@admin.register(TentAirQualityRecord)
class TentAirQualityRecordAdmin(admin.ModelAdmin):
    search_fields = ['created_at']
    list_display = ['id', 'tent', 'air_quality']

@admin.register(TentsWaterTank)
class TentsWaterTankAdmin(admin.ModelAdmin):
    search_fields = ['created_at', 'tent__company__name']
    list_display = ['id', 'tent', 'tank_number', 'sensor_sn', 'created_at']

@admin.register(WaterTankSensorHistory)
class WaterTankSensorHistoryAdmin(admin.ModelAdmin):
    search_fields = ['created_at']
    list_display = ['id', 'water_sensor', 'get_tent', 'water_level', 'water_level_percent', 'online', 'created_at']
    list_filter = ['created_at']
    
    def get_tent(self, obj):
        return obj.water_sensor.tent
    get_tent.short_description = 'Tent'
    
@admin.register(TentGate)
class TentGateAdmin(admin.ModelAdmin):
    search_fields = ['name', 'tent__name', 'tent__company__name']
    list_display = ['id', 'name', 'tent', 'get_company']
    list_filter = ['tent__company__name']
    autocomplete_fields = ['tent']

    def get_company(self, obj):
        return obj.tent.company.name if obj.tent and obj.tent.company else '—'
    get_company.short_description = 'Company'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ['name', 'name_ar']
    list_display = ['id','name', 'name_ar']