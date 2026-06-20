import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from faker import Faker
from django.utils import timezone
from camera.models import Camera, CleanIndicatorHistory, GuardPresenceHistory
from django.db import transaction

class Command(BaseCommand):
    help = 'Generate fake data for CleanIndicatorHistory and GuardPresenceHistory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10000,
            help='Number of fake records to create (for both CleanIndicatorHistory and GuardPresenceHistory)'
        )
        parser.add_argument(
            '--batch_size',
            type=int,
            default=500,
            help='Batch size for creating records'
        )

    def handle(self, *args, **options):
        fake = Faker()
        count = options['count']
        batch_size = options['batch_size']

        cameras = Camera.objects.all()
        if not cameras.exists():
            self.stdout.write(self.style.ERROR('No cameras found in the database.'))
            return

        def random_date():
            start_date = datetime(2025, 5, 1)
            end_date = datetime(2025, 12, 31)
            naive_datetime = fake.date_time_between(start_date=start_date, end_date=end_date)
            return timezone.make_aware(naive_datetime, timezone.get_current_timezone())

        min_records_per_camera = 200
        remaining_records = max(count - (min_records_per_camera * len(cameras)), 0)

        clean_batch = []
        guard_batch = []

        total_clean = 0
        total_guard = 0

        def save_batches():
            """Save current batch into the database."""
            nonlocal clean_batch, guard_batch
            if clean_batch:
                with transaction.atomic():
                    CleanIndicatorHistory.objects.bulk_create(clean_batch)
                    GuardPresenceHistory.objects.bulk_create(guard_batch)
                clean_batch = []
                guard_batch = []

        # 1. Ensure each camera has minimum 200 records
        for camera in cameras:
            for _ in range(min_records_per_camera):
                start_time = random_date()
                end_time = start_time + timedelta(hours=random.randint(1, 5))
                created_at = random_date()
                updated_at = created_at + timedelta(days=random.randint(0, 365))

                clean_batch.append(
                    CleanIndicatorHistory(
                        camera=camera,
                        is_clean=random.choice([True, False]),
                        start_time=start_time,
                        end_time=end_time,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
                guard_batch.append(
                    GuardPresenceHistory(
                        camera=camera,
                        present=random.choice([True, False]),
                        start_time=start_time,
                        end_time=end_time,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )

                if len(clean_batch) >= batch_size:
                    save_batches()

                total_clean += 1
                total_guard += 1

        # 2. Distribute remaining records across cameras
        if remaining_records > 0:
            extra_cameras = (
                list(cameras) * (remaining_records // len(cameras))
                + random.sample(list(cameras), remaining_records % len(cameras))
            )

            for camera in extra_cameras:
                start_time = random_date()
                end_time = start_time + timedelta(hours=random.randint(1, 5))
                created_at = random_date()
                updated_at = created_at + timedelta(days=random.randint(0, 100))

                clean_batch.append(
                    CleanIndicatorHistory(
                        camera=camera,
                        is_clean=random.choice([True, False]),
                        start_time=start_time,
                        end_time=end_time,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )
                guard_batch.append(
                    GuardPresenceHistory(
                        camera=camera,
                        present=random.choice([True, False]),
                        start_time=start_time,
                        end_time=end_time,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )

                if len(clean_batch) >= batch_size:
                    save_batches()

                total_clean += 1
                total_guard += 1

        # 3. Save any leftover objects
        save_batches()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {total_clean} CleanIndicatorHistory and {total_guard} GuardPresenceHistory records.'
        ))
