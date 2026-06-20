import csv
import requests
from django.core.management.base import BaseCommand
from sensor.models import EnvironmentSensor  # Adjust if needed


class Command(BaseCommand):
    help = 'Reads sensor neighbor data from Google Sheets CSV and updates EnvironmentSensor model'

    def handle(self, *args, **kwargs):
        # Replace this with your actual public Google Sheets CSV export link
        csv_url = "https://docs.google.com/spreadsheets/d/1LF_rBPssLgGY-qE6NNIk0hPzGGZ419oLSZWfB3Y3tqM/export?format=csv"

        try:
            response = requests.get(csv_url)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"❌ Error fetching CSV: {e}"))
            return

        decoded_content = response.content.decode('utf-8')
        reader = csv.DictReader(decoded_content.splitlines())

        updated_count = 0
        errors = []

        for row in reader:
            target_name = row.get('Target Device Name', '').strip()
            n1 = row.get('Neighbour Name 1', '').strip()
            n2 = row.get('Neighbour Name 2', '').strip()
            n3 = row.get('Neighbour Name 3', '').strip()

            if not target_name:
                errors.append("⚠️ Skipping row due to missing Target Device Name.")
                continue

            sensor = EnvironmentSensor.objects.filter(name=target_name).order_by('-last_entry_time').first()
            if not sensor:
                errors.append(f"Sensor '{target_name}' not found.")
                continue

            def get_sensor_by_name(name):
                return EnvironmentSensor.objects.filter(name=name).order_by('-last_entry_time').first() if name else None

            neighbour_1 = get_sensor_by_name(n1)
            neighbour_2 = get_sensor_by_name(n2)
            neighbour_3 = get_sensor_by_name(n3)

            if not neighbour_1:
                errors.append(f"{target_name}: Neighbour_1 '{n1}' not found.")
            if not neighbour_2:
                errors.append(f"{target_name}: Neighbour_2 '{n2}' not found.")
            if not neighbour_3:
                errors.append(f"{target_name}: Neighbour_3 '{n3}' not found.")

            sensor.neighbour_name_1 = neighbour_1
            sensor.neighbour_name_2 = neighbour_2
            sensor.neighbour_name_3 = neighbour_3
            sensor.check_neighbour = True
            sensor.save()
            updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"✅ Updated sensor {target_name}"))

        self.stdout.write(self.style.SUCCESS(f"\n✅ Finished. {updated_count} sensors updated."))

        if errors:
            self.stdout.write(self.style.WARNING("\n⚠️ Errors:"))
            for err in errors:
                self.stdout.write(self.style.WARNING(f"- {err}"))
