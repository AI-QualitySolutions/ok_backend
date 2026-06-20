import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from faker import Faker
from django.db import transaction
from django.utils.timezone import make_aware
from camera.models import Camera, CounterHistory

class Command(BaseCommand):
    help = 'Generate realistic fake data for CounterHistory (2024–2025)'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10000, help='Total number of fake records to create')
        parser.add_argument('--batch_size', type=int, default=5000, help='Number of records per batch')

    def handle(self, *args, **options):
        fake = Faker()
        count = options['count']
        batch_size = options['batch_size']

        cameras = Camera.objects.all()
        if not cameras.exists():
            self.stdout.write(self.style.ERROR('No cameras found in the database.'))
            return

        start_date = make_aware(datetime(2025, 5, 1)) # Start date: Year, Month, Day
        end_date = make_aware(datetime(2025, 12, 31))

        total_batches = (count + batch_size - 1) // batch_size  # ceil division

        self.stdout.write(self.style.WARNING(f'Starting to create {count} records in {total_batches} batches...'))

        for batch_num in range(total_batches):
            batch_size_now = min(batch_size, count - batch_num * batch_size)
            counter_history_objects = []

            for _ in range(batch_size_now):
                camera = random.choice(cameras)
                camera = camera
                sn = camera.sn
                created_at = make_aware(fake.date_time_between_dates(datetime_start=start_date, datetime_end=end_date))
                updated_at = created_at + timedelta(days=1)
                start_time = created_at - timedelta(seconds=20)
                end_time = created_at - timedelta(seconds=20)

                in_adult = random.randint(0, 500)
                in_child = random.randint(0, 200)
                total_in = in_adult + in_child

                out_adult = random.randint(0, in_adult)
                out_child = random.randint(0, in_child)
                total_out = out_adult + out_child

                passby_adult = random.randint(0, 100)
                passby_child = random.randint(0, 50)
                passby = passby_adult + passby_child

                turnback_adult = random.randint(0, 50)
                turnback_child = random.randint(0, 20)
                turnback = turnback_adult + turnback_child

                total = total_in + total_out
                avg_stay_time = random.randint(2500, 6500)

                counter_history_objects.append(
                    CounterHistory(
                        camera=camera,
                        sn=sn,
                        total_in=total_in,
                        total_out=total_out,
                        passby=0,
                        turnback=0,
                        avg_stay_time=0,
                        in_adult=0,
                        out_adult=0,
                        passby_adult=0,
                        turnback_adult=0,
                        in_child=0,
                        out_child=0,
                        passby_child=0,
                        turnback_child=0,
                        total=total,
                        start_time=start_time,
                        end_time=end_time,
                        created_at=created_at,
                        updated_at=updated_at,
                    )
                )

            with transaction.atomic():
                CounterHistory.objects.bulk_create(counter_history_objects, batch_size=batch_size)

            self.stdout.write(self.style.SUCCESS(f'Batch {batch_num + 1}/{total_batches} created successfully.'))

        self.stdout.write(self.style.SUCCESS(
            f'All {count} fake CounterHistory records created successfully!'
        ))
