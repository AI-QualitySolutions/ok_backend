# signals.py
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from sensor.models import SensorLocation, EnvironmentSensorRecord

@receiver(post_migrate)
def create_default_sensor_locations(sender, **kwargs):
    if sender.name != 'sensor':
        return

    default_locations = [
        "Kitchen", "Office", "Hall", "Entrance", "Exit", "Storage", "Corridor"
    ]

    for name in default_locations:
        SensorLocation.objects.get_or_create(name=name)
        
@receiver(post_save, sender=EnvironmentSensorRecord)
def update_environment_sensor(sender, instance, created, **kwargs):
    if created:
        sensor = instance.sensor
        # Check if last_entry_time is None or older
        if not sensor.last_entry_time or sensor.last_entry_time < instance.last_entry_time:
            sensor.tempareture = instance.tempareture
            sensor.humidity = instance.humidity
            sensor.last_entry_time = instance.last_entry_time
            sensor.save()

