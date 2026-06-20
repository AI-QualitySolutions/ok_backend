from celery import shared_task
import subprocess
from sensor.models import EnvironmentSensorRecord, EnvironmentSensor
import numpy as np
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.core.management import call_command

import random

import logging

logger = logging.getLogger(__name__)

@shared_task
def collect_sensor_data_task():
    #subprocess.run(['python', 'manage.py', 'collect_sensor_data'])
    call_command('collect_sensor_data')
    
        
#@shared_task
#def generate_fake_environment_data():
#    now = timezone.now()
#    sensors = EnvironmentSensor.objects.filter(type="environment")

#    for sensor in sensors:
#        # Generate correlated values
#        base_temp = random.randint(10, 30)  # Typical indoor range
#        temp = np.clip(base_temp + random.randint(-5, 5), 0, 50)
        
#        # Humidity inversely related to temperature
#        base_humidity = random.randint(30, 70)
#        humidity = np.clip(base_humidity + (25 - (temp - 20)), 0, 100)

#        # Create 15-minute interval
#        start_time = now
#        end_time = start_time + timedelta(minutes=15)

#        EnvironmentSensorRecord.objects.create(
#            sensor=sensor,
#            tempareture=temp,  # Note: Field name matches your model's spelling
#            humidity=humidity,
#            last_entry_time=now,
#            start_time=start_time,
#            end_time=end_time
#        )

#    logger.info(f"Generated {len(sensors)} environment sensor records")