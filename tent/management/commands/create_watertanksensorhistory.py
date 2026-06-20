import random
from django.core.management.base import BaseCommand
from faker import Faker
import pytz
from django.utils import timezone
# Replace with your actual app name
from tent.models import WaterTankSensorHistory, TentsWaterTank
from datetime import datetime, timedelta

from datetime import datetime


class Command(BaseCommand):
    help = 'Generate fake water tank sensor history records'

    def handle(self, *args, **kwargs):
        fake = Faker()
        tzinfo = pytz.UTC  # Replace with your preferred timezone if needed

        # Define date range as datetime objects
        start_date = datetime(2025, 5, 1, tzinfo=tzinfo)
        end_date = datetime(2025, 12, 31, tzinfo=tzinfo)

        # Fetch all water tanks to generate data for
        water_tanks = TentsWaterTank.objects.all()

        if not water_tanks:
            self.stdout.write(self.style.WARNING(
                'No water tanks found in the database. Please add water tanks first.'))
            return

        records_to_create = 0
        batch_size = 5000

        for water_tank in water_tanks:
            records_per_tank = 1000  # Changed from 5000 to 1000
            bulk_data = []

            for _ in range(records_per_tank):
                start_time = fake.date_time_between(
                    start_date=start_date, end_date=end_date, tzinfo=tzinfo)
                end_time = start_time + \
                    timedelta(minutes=random.randint(1, 1440))

                created_at = fake.date_time_between_dates(
                    datetime_start=start_time - timedelta(days=1),
                    datetime_end=start_time,
                    tzinfo=tzinfo
                )
                updated_at = created_at + \
                    timedelta(minutes=random.randint(1, 1440))
                is_online = random.choice([True, False])
                if is_online:
                    water_level = round(random.uniform(0, 70), 2)
                    water_level_percent = round(water_level / 70 * 100, 2)
                else:
                    water_level = 0.0
                    water_level_percent = 0.0
                bulk_data.append(WaterTankSensorHistory(
                    water_sensor=water_tank,
                    water_level=water_level,
                    water_level_percent=water_level_percent,
                    online=is_online,
                    start_time=start_time,
                    end_time=end_time,
                    created_at=created_at,
                    updated_at=updated_at
                ))

                if len(bulk_data) >= batch_size:
                    WaterTankSensorHistory.objects.bulk_create(bulk_data)
                    self.stdout.write(self.style.SUCCESS(
                        f'Inserted {len(bulk_data)} records for water tank {water_tank.tank_number}.'))
                    bulk_data = []

            if bulk_data:
                WaterTankSensorHistory.objects.bulk_create(bulk_data)
                self.stdout.write(self.style.SUCCESS(
                    f'Inserted remaining {len(bulk_data)} records for water tank {water_tank.tank_number}.'))

            records_to_create += records_per_tank

        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated and inserted {records_to_create} fake water tank sensor history records.'))
