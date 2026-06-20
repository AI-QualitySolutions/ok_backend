import json
import random
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, get_default_timezone
from datetime import datetime, timedelta
from tent.models import  Tent
from camera.models import Camera

class Command(BaseCommand):
    help = "Insert camera data from a JSON file and associate them with random tents"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help="Path to the JSON file containing camera data")

    def random_datetime(self, start_year, end_year):
        """Generate a random timezone-aware datetime between two years."""
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year, 12, 31, 23, 59, 59)
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))
        naive_datetime = start_date + timedelta(seconds=random_seconds)
        return make_aware(naive_datetime, timezone=get_default_timezone())

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            # Load JSON data from the file
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # Fetch all tent instances from the database
            tents = Tent.objects.all()

            if not tents:
                self.stderr.write(self.style.ERROR("No tents found in the database"))
                return

            for item in data:
                # Generate random created_at and updated_at times
                created_at = self.random_datetime(2024, 2025)
                updated_at = created_at + timedelta(days=random.randint(1, 365))  # Ensure updated_at > created_at

                # Randomly choose a tent (between 0 and 2 cameras per tent)
                number_of_cameras = random.randint(0, 2)

                for _ in range(number_of_cameras):
                    # Generate random serial number for the camera
                    camera_sn = f"CAM{random.randint(100000, 999999)}"  # Generate a random serial number
                    camera = Camera.objects.create(
                        sn=camera_sn,
                        created_at=created_at,
                        updated_at=updated_at,
                        tent=random.choice(tents),  # Randomly assign a tent
                    )

                self.stdout.write(self.style.SUCCESS(f"Inserted {number_of_cameras} camera(s) for Tent"))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON format in file: {file_path}"))
