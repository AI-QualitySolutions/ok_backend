from celery import shared_task
import requests
from weight.models import OrderWeight
from tent.models import TentAirQualityRecord, Tent, TentsWaterTank, WaterTankSensorHistory
from celery import shared_task
import subprocess
from sensor.models import EnvironmentSensorRecord, EnvironmentSensor
import numpy as np
from datetime import timedelta
from django.utils import timezone
from celery import shared_task
import hashlib
import random

import logging

logger = logging.getLogger(__name__)

# @shared_task
# def clear_session_cache(id):
#     # Clear the session cache for the given user ID
#     print(f"Clearing session cache for user {id}")
#     return id





@shared_task
def fetch_and_store_data():
    """
    Fetch data from an API and store it in the OrderWeight model.

    :param user_id: Optional user ID for additional processing.
    """
    try:
        api_url = "http://projectegy-002-site44.gtempurl.com/api/Account/AllOrders"
        # Make an API call
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)

        # Process the response
        data = response.json()

        # Insert data into the database
        for item in data:
            OrderWeight.objects.create(
                device_num=item.get('deviceNum'),
                weight=item.get('weight'),
                date=item.get('date'),
                is_modified=item.get('isModified', False),
                is_deleted=item.get('isDeleted', False),
                deleted_on=item.get('deletedOn'),
                updated_at = item.get('modifiedOn') ,
                created_at=item.get('createdOn'),
            )
        return f"Successfully stored data."
    except requests.exceptions.RequestException as e:
        return f"API call failed: {e}"
    except Exception as e:
        return f"Error while storing data: {e}"



@shared_task
def generate_fake_order_weight_data():
    sensors = EnvironmentSensor.objects.filter(type="weight")
    start_date = timezone.now() - timedelta(days=365)


    for sensor in sensors:
        # Random time in last year with realistic working hours (8am-8pm)
        rand_hours = random.randint(8, 19)
        rand_minutes = random.choice([0, 15, 30, 45])
        date = start_date + timedelta(
            days=random.randint(0, 365),
            hours=rand_hours,
            minutes=rand_minutes
        )

        # Weight distribution with common package weights
        base_weight = random.choice([250, 300, 350, 400, 450, 500])
        weight = round(base_weight + random.uniform(-0.3, 0.3), 2)

        # 15% chance of modification with realistic patterns
        is_modified = random.random() < 0.15
        secret = None
        if is_modified:
            # Generate plausible "correction" factors
            weight *= random.choice([0.9, 1.1])
            weight = round(weight, 2)
            secret = hashlib.sha256(f"{date}-{weight}".encode()).hexdigest()[:20]

        # 5% deletion rate with admin-like patterns
        is_deleted = random.random() < 0.05
        deleted_on = None
        if is_deleted:
            deleted_on = date + timedelta(hours=random.randint(1, 72))

        # OrderWeight.objects.create(
        #     device_num=sensor.sn,
        #     weight=weight,
        #     date=date,
        #     is_modified=is_modified,
        #     is_deleted=is_deleted,
        #     deleted_on=deleted_on,
        #     secret=secret,
        #     weight_sensor=sensor
        # )

    logger.info("Generated 200 order weight records with realistic patterns")