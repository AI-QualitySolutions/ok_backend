import random
from django.core.management.base import BaseCommand
from faker import Faker
from sensor.models import EnvironmentSensor, Tent
from datetime import datetime, timedelta
from django.utils import timezone
import pytz


class Command(BaseCommand):
    help = 'Generate fake environment sensor data for 2024–2025 with proper naming like "tent.name-index"'

    def handle(self, *args, **kwargs):
        fake = Faker()
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 12, 31)
        tzinfo = pytz.UTC

        sensors_to_create = []


        for i in range(1, 201):  # Generate 200 sensors
            sn = fake.unique.uuid4().replace("-", "")[:16]
            ip = fake.ipv4() if random.choice([True, False]) else None
            temperature = random.randint(27, 40)
            humidity = random.randint(30, 70)
            online = random.choice([True, False])

            created_at = fake.date_time_between(start_date=start_date, end_date=end_date, tzinfo=tzinfo)
            updated_at = created_at + timedelta(minutes=random.randint(1, 1440))
            last_entry_time = fake.date_time_between(start_date=start_date, end_date=end_date, tzinfo=tzinfo)

     
            sensor_name = EnvironmentSensor.objects.all().count()+i
            sensor = EnvironmentSensor(
                tent=None,
                sn=sn,
                name=sensor_name,
                ip=ip,
                lat=None,
                long=None,
                location=None,
                top=None,
                left=None,
                online=online,
                tempareture=temperature,
                humidity=humidity,
                last_entry_time=last_entry_time,
                created_at=created_at,
                updated_at=updated_at
            )
            sensors_to_create.append(sensor)

        EnvironmentSensor.objects.bulk_create(sensors_to_create)
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(sensors_to_create)} EnvironmentSensors.'))
