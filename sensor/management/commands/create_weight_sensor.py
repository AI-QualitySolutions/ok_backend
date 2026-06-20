import random
from django.core.management.base import BaseCommand
from faker import Faker
from sensor.models import EnvironmentSensor, Tent
from datetime import datetime, timedelta
from django.utils import timezone
import pytz


class Command(BaseCommand):
    help = 'Generate fake environment sensor data for 2024-2025 with proper naming like "tent.name-index"'

    def handle(self, *args, **kwargs):
        fake = Faker()
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 12, 31)
        tzinfo = pytz.UTC

        location_choices = ["Kitchen", "Office", "Hall",
                            "Entrance", "Exit", "Storage", "Corridor"]

        tents = list(Tent.objects.all())
        if not tents:
            self.stdout.write(self.style.WARNING(
                'No tents found in the database.'))
            return

        for tent in tents:
            sensors_to_create = []
            for index in range(1, 5):
                sn = fake.unique.uuid4().replace("-", "")[:16]
                name = f"{tent.name}-{index}"
                ip = fake.ipv4() if random.choice([True, False]) else None
                lat = round(random.uniform(20.0, 22.0), 6)
                long = round(random.uniform(39.0, 41.0), 6)
                location = random.choice(location_choices)
                top = round(random.uniform(0, 100), 2) if random.choice(
                    [True, False]) else None
                left = round(random.uniform(0, 100), 2) if random.choice(
                    [True, False]) else None
                online = random.choice([True, False])
                temperature = random.randint(250, 300)
                humidity = random.randint(30, 70)

                last_entry_time = fake.date_time_between(
                    start_date=start_date, end_date=end_date)
                created_at = fake.date_time_between(
                    start_date=start_date, end_date=end_date, tzinfo=tzinfo)

                if created_at.tzinfo is None:
                    created_at = timezone.make_aware(
                        created_at, timezone=tzinfo)

                updated_at = created_at + \
                    timedelta(minutes=random.randint(1, 1440))

                if last_entry_time.tzinfo is None:
                    last_entry_time = timezone.make_aware(
                        last_entry_time, timezone=tzinfo)

                sensor = EnvironmentSensor(
                    tent=tent,
                    sn=sn,
                    name=name,
                    ip=ip,
                    lat=lat,
                    long=long,
                    location=location,
                    top=top,
                    left=left,
                    online=online,
                    tempareture=temperature,
                    humidity=humidity,
                    last_entry_time=last_entry_time,
                    created_at=created_at,
                    updated_at=updated_at,
                    type="weight"
                )
                sensors_to_create.append(sensor)

            EnvironmentSensor.objects.bulk_create(sensors_to_create)
            self.stdout.write(self.style.SUCCESS(
                f'✅ Created 100 Weight Sensors for tent "{tent.name}"'))

        self.stdout.write(self.style.SUCCESS(
            '🎉 Successfully generated all Weight Sensors.'))
