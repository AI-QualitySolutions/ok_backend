import random
from django.core.management.base import BaseCommand
from faker import Faker
import pytz
from django.utils import timezone
# Replace 'yourapp' with your actual app name
from tent.models import TentsWaterTank, Tent
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Generate 5 fake water tank records per tent'

    def handle(self, *args, **kwargs):
        fake = Faker()
        tzinfo = pytz.UTC

        start_date = datetime(2025, 5, 1, tzinfo=tzinfo)
        end_date = datetime(2025, 12, 31, tzinfo=tzinfo)

        tents = Tent.objects.all()

        if not tents.exists():
            self.stdout.write(self.style.WARNING(
                'No tents found in the database. Please add tents first.'))
            return

        records_to_create = 0
        data = []

        for tent in tents:
            for _ in range(5):  # Generate exactly 5 tanks per tent
                tank_number = fake.unique.random_number(digits=6)
                sensor_sn = fake.unique.uuid4()

                created_at = fake.date_time_between(
                    start_date=start_date, end_date=end_date, tzinfo=tzinfo)
                random_delta = timedelta(minutes=random.randint(1, 1440))
                updated_at = min(created_at + random_delta, end_date)

                data.append(TentsWaterTank(
                    tent=tent,
                    tank_number=tank_number,
                    sensor_sn=sensor_sn,
                    created_at=created_at,
                    updated_at=updated_at,
                ))
                records_to_create += 1

        TentsWaterTank.objects.bulk_create(data, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated {records_to_create} fake water tank records (5 per tent).'))
