from tent.models import TentAirQualityRecord, Tent, TentsWaterTank, WaterTankSensorHistory
from celery import shared_task
import subprocess
from sensor.models import EnvironmentSensorRecord, EnvironmentSensor
import numpy as np
from datetime import timedelta
from django.utils import timezone
from celery import shared_task

import random

import logging

logger = logging.getLogger(__name__)
@shared_task
def generate_fake_tent_air_quality():
    tents = Tent.objects.all()

    for tent in tents:
        
        air_quality = random.randint(20, 45)

        TentAirQualityRecord.objects.create(
            tent=tent,
            air_quality=air_quality
        )

    logger.info(f"Generated {len(tents)} environment sensor records")
    
    
@shared_task
def generate_fake_water_tank_data():
    now = timezone.now()
    tanks = TentsWaterTank.objects.all()

    for tank in tanks:
        start_time = now
        end_time = start_time + timedelta(minutes=15)
        online = np.random.choice([True, False], p=[0.85, 0.15])  # 85% online chance

        if online:
            # Simulate realistic water patterns (0-1000 liters assumed capacity)
            base_level = random.uniform(0, 1000)
            water_level = round(np.clip(base_level + random.uniform(-50, 50), 0, 1000), 2)
            water_level_percent = round((water_level / 1000) * 100, 2)
        else:
            water_level = None
            water_level_percent = None



        # Create record
        WaterTankSensorHistory.objects.create(
            water_sensor=tank,
            water_level=water_level,
            water_level_percent=water_level_percent,
            online=online,
            start_time=start_time,
            end_time=end_time,
        )

    logger.info(f"Generated {len(tanks)} water tank records")