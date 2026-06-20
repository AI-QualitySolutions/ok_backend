from django.db import models
from tent.models import Tent
from authentication.models import BaseModel


class SensorLocation(BaseModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class EnvironmentSensor(BaseModel):
    type_sensor=[
		("environment","environment"),
		("weight","weight"),
	]
    tent = models.ForeignKey(Tent, on_delete=models.CASCADE, null=True, blank=True, related_name="sensors")
    sn = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, default="")
    ip = models.CharField(max_length=255, null=True, blank=True)
    lat = models.CharField(max_length=255, null=True, blank=True)
    long = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    top = models.FloatField(blank=True, null=True)
    left = models.FloatField(null=True,blank=True)
    online = models.BooleanField(default=False)
    tempareture = models.FloatField(default=0)
    humidity = models.IntegerField(default=0)
    last_entry_time = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=255, choices=type_sensor, default="environment")
    neighbour_name_1 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='neighbour_1_of',
        verbose_name='Neighbour Name 1'
    )

    neighbour_name_2 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='neighbour_2_of',
        verbose_name='Neighbour Name 2'
    )

    neighbour_name_3 = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='neighbour_3_of',
        verbose_name='Neighbour Name 3'
    )
    check_neighbour = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tent} -> {self.name} -> {self.type}"
    
    class Meta:
        ordering = ["sn"]


class EnvironmentSensorRecord(BaseModel):
    sensor = models.ForeignKey(EnvironmentSensor, on_delete=models.CASCADE)
    tempareture = models.FloatField(default=0)
    humidity = models.IntegerField(default=0)
    last_entry_time = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    update_from_neighbour = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["sensor", "-created_at"], name="envsensrec_sensor_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.sensor.sn}"
