import random
from django.core.management.base import BaseCommand
from faker import Faker
import pytz
from django.utils import timezone
from tent.models import TentAirQualityRecord, Tent  # Replace 'yourapp' with your actual app name
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Generate fake tent air quality records'

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

        total_records = 0
        all_data = []

        for tent in tents:
            for _ in range(50):  # 50 records per tent
                air_quality = random.randint(20, 45)

                created_at = fake.date_time_between(
                    start_date=start_date, end_date=end_date, tzinfo=tzinfo)
                random_delta = timedelta(
                    minutes=random.randint(1, 1440))  # 1 min to 24 hrs
                updated_at = created_at + random_delta
                if updated_at > end_date:
                    updated_at = end_date

                all_data.append(TentAirQualityRecord(
                    tent=tent,
                    air_quality=air_quality,
                    created_at=created_at,
                    updated_at=updated_at
                ))
                total_records += 1

        TentAirQualityRecord.objects.bulk_create(all_data, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully generated {total_records} tent air quality records ({len(tents)} tents × 50).'))
