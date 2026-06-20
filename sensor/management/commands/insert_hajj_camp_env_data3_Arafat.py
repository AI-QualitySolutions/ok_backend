import csv
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
import pytz

from sensor.models import EnvironmentSensor, EnvironmentSensorRecord


class Command(BaseCommand):
    help = "Import environment sensor records from CSV using sensor.name (non-unique)"

    def handle(self, *args, **options):
        csv_file_path = "hajj_camp_env_data3_Arafat.csv"
        riyadh_tz = pytz.timezone("Asia/Riyadh")

        with open(csv_file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

            if len(rows) < 3:
                self.stdout.write(self.style.ERROR("CSV file must have at least 3 rows"))
                return

            # --- Parse sensor mapping ---
            name_row = rows[0]     # First row: sensor.name values (can be duplicate)
            header_row = rows[1]   # Second row: temp_1, hum_1, ...

            sensor_column_map = {}  # {column_index: (sensor_name, value_type)}
            for idx, (name, label) in enumerate(zip(name_row, header_row)):
                if idx < 2:  # skip day/time
                    continue
                name = name.strip()
                label = label.strip().lower()
                if name and (label.startswith("temp") or label.startswith("hum")):
                    sensor_column_map[idx] = (name, label)

            # --- Preload all sensors into dict: name -> list of sensors ---
            all_sensors = EnvironmentSensor.objects.all()
            sensor_map_by_name = {}

            for sensor in all_sensors:
                key = sensor.name.strip()
                sensor_map_by_name.setdefault(key, []).append(sensor)

            # --- Process each data row ---
            for row in rows[2:]:  # skip first 2 header rows
                if not row or len(row) < 2:
                    continue

                date_str = row[0].strip()
                time_str = row[1].strip()

                try:
                    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %H:%M")
                    dt = riyadh_tz.localize(dt_naive)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Invalid datetime: {date_str} {time_str} - {e}"))
                    continue

                # Map sensor_name -> {'tempareture': value, 'humidity': value}
                values_map = {}
                for idx in range(2, len(row)):
                    if idx not in sensor_column_map:
                        continue
                    name, field_type = sensor_column_map[idx]
                    value = row[idx].strip()
                    if not value:
                        continue
                    try:
                        val = float(value)
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Invalid value '{value}' at column {idx}"))
                        continue

                    if name not in values_map:
                        values_map[name] = {}
                    if "temp" in field_type:
                        values_map[name]["tempareture"] = val
                    elif "hum" in field_type:
                        values_map[name]["humidity"] = int(val)
                # Create records
                for name, data in values_map.items():
                    sensor_list = sensor_map_by_name.get(name)
                    if not sensor_list:
                        self.stdout.write(self.style.WARNING(f"Sensor with name '{name}' not found"))
                        continue

                    sensor = sensor_list[0]  # Pick first if multiple sensors with same name

                    if "tempareture" in data and "humidity" in data:
                        EnvironmentSensorRecord.objects.create(
                            sensor=sensor,
                            tempareture=data["tempareture"],
                            humidity=data["humidity"],
                            last_entry_time=dt,
                            start_time=dt,
                            end_time=dt + timedelta(minutes=5),
                            update_from_neighbour=False
                        )

        self.stdout.write(self.style.SUCCESS("✅ Sensor records imported successfully."))
