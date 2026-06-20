import json
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware, get_default_timezone
from tent.models import Tent  # Replace 'your_app' with the actual app name


class Command(BaseCommand):
    help = "Insert tent data from a JSON file into the database with random created_at and updated_at values"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help="Path to the JSON file")

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
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            for item in data:
                # Generate random created_at and updated_at
                created_at = self.random_datetime(2024, 2025)
                updated_at = created_at + timedelta(days=random.randint(1, 365))  # Ensure updated_at > created_at
                if Tent.objects.filter(name=item.get("name")).exists():
                    self.stderr.write(self.style.ERROR(f"Already exists: {item.get('name')}"))
                    continue
                tent = Tent.objects.create(
                    name=item.get("name"),
                    latitude=item.get("lat"),
                    longitude=item.get("long"),
                    location=item.get("location"),
                    capacity=item.get("capacity"),
                    air_condition=item.get("air_condition"),
                    air_condition_update_time=item.get("air_condition_update_time"),
                    is_arafa=item.get("is_arafa"),
                    max_adjust_tempareture=item.get("max_adjust_tempareture"),
                    avg_adjust_tempareture=item.get("avg_adjust_tempareture"),
                    min_adjust_tempareture=item.get("min_adjust_tempareture"),
                    is_adjust_tempareture=item.get("is_adjust_tempareture"),
                    max_adjust_humidity=item.get("max_adjust_humidity"),
                    avg_adjust_humidity=item.get("avg_adjust_humidity"),
                    min_adjust_humidity=item.get("min_adjust_humidity"),
                    is_adjust_humidity=item.get("is_adjust_humidity"),
                )
                # tent, created = Tent.objects.update_or_create(
                #     pk=item.get("pk"),
                #     defaults={
                #         "name": item.get("name"),
                #         "latitude": item.get("lat"),
                #         "longitude": item.get("long"),
                #         "location": item.get("location"),
                #         "capacity": item.get("capacity"),
                #         "air_condition": item.get("air_condition"),
                #         "air_condition_update_time": item.get("air_condition_update_time"),
                #         "is_arafa": item.get("is_arafa"),
                #         "max_adjust_tempareture": item.get("max_adjust_tempareture"),
                #         "avg_adjust_tempareture": item.get("avg_adjust_tempareture"),
                #         "min_adjust_tempareture": item.get("min_adjust_tempareture"),
                #         "is_adjust_tempareture": item.get("is_adjust_tempareture"),
                #         "max_adjust_humidity": item.get("max_adjust_humidity"),
                #         "avg_adjust_humidity": item.get("avg_adjust_humidity"),
                #         "min_adjust_humidity": item.get("min_adjust_humidity"),
                #         "is_adjust_humidity": item.get("is_adjust_humidity"),
                #     }
                # )

                # Set random created_at and updated_at
                tent.created_at = created_at
                tent.updated_at = updated_at
                tent.save()

            self.stdout.write(self.style.SUCCESS("Data successfully inserted into the Tent model from JSON ."))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found: {file_path}"))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON format in file: {file_path}"))
