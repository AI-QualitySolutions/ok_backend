from django.db import models
from authentication.models import BaseModel
from tent.models import Tent
from sensor.models import EnvironmentSensor

rejected_Under = 60

class OrderWeight(BaseModel):
    device_num = models.CharField(max_length=255)
    weight = models.FloatField()
    date = models.DateTimeField()
    is_modified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_on = models.DateTimeField(null=True, blank=True)
    secret = models.CharField(max_length=255, null=True, blank=True)
    weight_sensor = models.ForeignKey(EnvironmentSensor, on_delete=models.CASCADE, null=True, blank=True, related_name="order_weights")

    def __str__(self):
        return f"Device {self.device_num} - ID {self.id}"

class WeightConditions(BaseModel):
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    breakfast_start = models.TimeField(null=True, blank=True)
    breakfast_end = models.TimeField(null=True, blank=True)
    lunch_start = models.TimeField(null=True, blank=True)
    lunch_end = models.TimeField(null=True, blank=True)
    dinner_start = models.TimeField(null=True, blank=True)
    dinner_end = models.TimeField(null=True, blank=True)
    breakfast_weight_accepted = models.FloatField(null=True, blank=True)
    lunch_weight_accepted = models.FloatField(null=True, blank=True)
    dinner_weight_accepted = models.FloatField(null=True, blank=True)


    class Meta:
        verbose_name = "Weight Condition"
        verbose_name_plural = "Weight Conditions"
        ordering = ['start_date']  # Optionally order by start_date if you need

    def __str__(self):
        # Improved string representation with conditionals to handle null values
        start = self.start_date.strftime('%Y-%m-%d %H:%M:%S') if self.start_date else 'Not specified'
        end = self.end_date.strftime('%Y-%m-%d %H:%M:%S') if self.end_date else 'Not specified'
        return f"Weight Conditions from {start} to {end}"