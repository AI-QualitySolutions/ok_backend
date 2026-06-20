import random
import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from faker import Faker
from camera.models import KitchenViolationReport, Camera


class Command(BaseCommand):
    help = 'Generate fake KitchenViolationReport data'

    def handle(self, *args, **kwargs):
        fake = Faker()
        cameras = Camera.objects.all()
        if not cameras:
            self.stderr.write("No cameras found. Please add cameras first.")
            return

        total_records = 100000
        reports = []

        start_date = timezone.make_aware(datetime(2025, 5, 1))
        end_date = timezone.make_aware(datetime(2025, 12, 31))

        for _ in range(total_records):
            camera = random.choice(cameras)

            start_time = fake.date_time_between_dates(
                datetime_start=start_date, datetime_end=end_date)
            start_time = timezone.make_aware(start_time)

            end_time = start_time + timedelta(minutes=random.randint(10, 90))

            violation = random.choice([True, False])
            violation_list = (
                [{"type": "Uncovered head", "time": str(start_time.time())},
                 {"type": "Improper hygiene", "time": str((start_time + timedelta(minutes=5)).time())}]
                if violation else None
            )

            report = KitchenViolationReport(
                camera=camera,
                violation=violation,
                violation_list=violation_list,
                start_time=start_time,
                end_time=end_time,
                image=None  # or fake.image_url() if using a placeholder path
            )
            reports.append(report)

        KitchenViolationReport.objects.bulk_create(reports)
        self.stdout.write(self.style.SUCCESS(
            f"Successfully created {total_records} fake KitchenViolationReport records."))
