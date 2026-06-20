from django.core.management.base import BaseCommand
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils.timezone import make_aware
from camera.models import Camera, GuardPresenceHistory
import random
from faker import Faker
from tqdm import tqdm
from django.db import transaction


class Command(BaseCommand):
    help = 'Generate fake guard presence history data with continuous timeline like sensor records'

    def handle(self, *args, **kwargs):
        fake = Faker()
        cameras = Camera.objects.filter(type="guard").first()
        print(cameras)

        if not cameras:
            self.stdout.write(self.style.WARNING(
                'No cameras found in the database. Please add cameras first.'))
            return

        # Time range: May 1, 2025 – June 1, 2025
        start_range = datetime(2025, 6, 1, 0, 0, 0,
                               tzinfo=dt_timezone(timedelta(hours=6)))
        end_range = datetime(2025, 7, 1, 0, 0, 0,
                             tzinfo=dt_timezone(timedelta(hours=6)))

        batch_size = 1000
        total_records_created = 0
        current_time = start_range
        batch_data = []
        records_count = 0

        try:
            with transaction.atomic():
                while current_time < end_range:
                    # Duration of guard presence: 1–5 minutes
                    duration_minutes = random.randint(1, 5)
                    end_time = current_time + \
                        timedelta(minutes=duration_minutes)

                    # Guard present or not
                    present = random.choice([True, False])
                    guard_count = random.randint(1, 8) if present else 0

                    batch_data.append(
                        GuardPresenceHistory(
                            camera=cameras,
                            guard_count=guard_count,
                            current_status=["absent"] if guard_count == 0 else [str(guard_count)],
                            present=present,
                            start_time=current_time,
                            end_time=end_time
                        )
                    )
                    records_count += 1

                    # Gap between this record and the next one: 1–40 minutes
                    gap_minutes = random.randint(1, 17)
                    current_time = end_time + \
                        timedelta(minutes=gap_minutes)

                    if len(batch_data) >= batch_size:
                        GuardPresenceHistory.objects.bulk_create(
                            batch_data)
                        total_records_created += len(batch_data)
                        batch_data = []

                # Insert remaining records
                if batch_data:
                    GuardPresenceHistory.objects.bulk_create(batch_data)
                    total_records_created += len(batch_data)

            self.stdout.write(self.style.SUCCESS(
                f'Created {records_count} records for camera {cameras.sn}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Failed to create records for camera {cameras.sn}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(
            f'Guard presence data generation complete. Total records created: {total_records_created}'
        ))
