import json
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, get_default_timezone
from authentication.models import BaseModel
from sensor.models import EnvironmentSensor
from tent.models import Tent


class Command(BaseCommand):
    help = 'Insert EnvironmentSensor data from JSON file into the database'

    def add_arguments(self, parser):
        # Accept file_path as a positional argument
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the JSON file containing EnvironmentSensor data',
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            tents = Tent.objects.all()

            for item in data:
                # Generate random created_at and updated_at times (make them timezone-aware)
                created_at = self.random_datetime(2025, 2025)
                updated_at = created_at + timedelta(days=random.randint(1, 365))  # Ensure updated_at > created_at

                # Make sure both created_at and updated_at are timezone-aware
                created_at = make_aware(created_at, timezone=get_default_timezone())
                updated_at = make_aware(updated_at, timezone=get_default_timezone())

                # Convert the 'last_entry_time' from JSON to a timezone-aware datetime
                last_entry_time_str = item.get('last_entry_time')
                last_entry_time = None
                if last_entry_time_str:
                    naive_last_entry_time = datetime.fromisoformat(last_entry_time_str)
                    last_entry_time = make_aware(naive_last_entry_time, timezone=get_default_timezone())

                # Randomly choose tent if tent id exists in JSON, else set tent to None
                random_tent = random.choice(tents) if tents else None

                # Create the EnvironmentSensor instance
                sensor = EnvironmentSensor.objects.create(
                    sn=item['sn'],
                    name=item.get('name', ''),
                    lat=item.get('lat', ''),
                    long=item.get('long', ''),
                    location=item.get('location', ''),
                    online=random.choice([True, False]),
                    tempareture=item.get('tempareture', 0),
                    humidity=item.get('humidity', 0),
                    last_entry_time=last_entry_time,  # Make sure it's timezone-aware
                    created_at=created_at,
                    updated_at=updated_at,
                    tent=random_tent,
                    top=item.get('top', None),
                    left=item.get('left', None),
                    type=random.choice(EnvironmentSensor.type_sensor)[0],
                )

                self.stdout.write(self.style.SUCCESS(f"Inserted sensor {sensor.sn}"))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON format in file: {file_path}"))

    def random_datetime(self, start_year, end_year):
        """Generate a random datetime between start_year and end_year."""
        start_date = datetime(start_year, 5, 1)
        end_date = datetime(end_year, 12, 31)
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        random_datetime = start_date + timedelta(days=random_days)
        return random_datetime
