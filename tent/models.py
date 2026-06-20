from django.db import models
from authentication.models import BaseModel, Company

class Country(BaseModel):
    name = models.CharField(max_length=255, null=False, blank=False)
    name_ar = models.CharField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['id']
class Tent(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, blank=False, related_name="tent")
    name = models.CharField(max_length=255, null=False, blank=False)
    longitude = models.CharField(max_length=255, null=False, blank=False)
    latitude = models.CharField(max_length=255, null=False, blank=False)
    location = models.TextField(null=True, blank=True)
    map_image = models.ImageField(
        upload_to='images/%Y/%m/%d/', blank=True, null=True)
    created_by = models.ForeignKey(
        "authentication.MyUser", on_delete=models.SET_NULL, null=True, blank=True
    )

    tent_image = models.ImageField(
        upload_to='images_tent/%Y/%m/%d/', blank=True, null=True)

    air_condition = models.IntegerField(null=True, blank=True)
    air_condition_update_time = models.DateTimeField(null=True, blank=True)

    capacity = models.IntegerField(default=0)
    staying = models.IntegerField(default=0)
    is_arafa = models.BooleanField(default=False, db_index=True)

    adjust = models.IntegerField(default=0)
    fixed = models.BooleanField(default=False)

    max_adjust_tempareture = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    avg_adjust_tempareture = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    min_adjust_tempareture = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    is_adjust_tempareture = models.BooleanField(default=False)
    max_adjust_humidity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    avg_adjust_humidity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    min_adjust_humidity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    is_adjust_humidity = models.BooleanField(default=False)

    nationality = models.ManyToManyField(Country, blank=True)

    def __str__(self):
        company_name = self.company.name if self.company else "No Company"
        arafa = "Arafa" if self.is_arafa else "Mina"
        return f"Tent Pk: {self.pk} -> Tent Name: {self.name} -> {arafa} -> Company: {company_name}"


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'name', 'is_arafa'], name='unique_company_tent_name')
        ]


class TentGate(BaseModel):
    tent = models.ForeignKey(Tent, on_delete=models.CASCADE, related_name='gates')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.tent.name} - {self.name}"


class TentAirQualityRecord(BaseModel):
    tent = models.ForeignKey(Tent, on_delete=models.CASCADE)
    air_quality = models.IntegerField()


class TentsWaterTank(BaseModel):
    tent = models.ForeignKey(
        Tent, on_delete=models.CASCADE, related_name='water_tanks')
    tank_number = models.CharField(
        max_length=255, null=False, blank=False, unique=True)
    sensor_sn = models.CharField(
        max_length=255, null=True, blank=True, unique=True)

    def __str__(self):
        return f"Building Tank Number {self.tank_number} for {self.tent.id}"


class WaterTankSensorHistory(BaseModel):
    water_sensor = models.ForeignKey(
        TentsWaterTank, on_delete=models.CASCADE, null=False, blank=False, related_name="sensor_history")
    water_level = models.FloatField(null=True, blank=True)
    water_level_percent = models.FloatField(null=True, blank=True)
    online = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["water_sensor", "-end_time"], name="watertank_sensor_end_idx"),
        ]

    def __str__(self):
        return f"Water Sensor {self.water_sensor.tank_number}"
