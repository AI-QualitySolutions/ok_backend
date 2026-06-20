import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord


class Command(BaseCommand):
    help = "Delete existing records and recreate them using neighbor data (from 6 June 2025, 12:00 AM Riyadh time)."

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        interval = timedelta(minutes=5)

        # Time range
        start_time = riyadh_tz.localize(datetime(2025, 6, 6, 0, 0, 0))
        end_time = riyadh_tz.localize(datetime(2025, 6, 6, 21, 0, 0))

        sensors = EnvironmentSensor.objects.filter(check_neighbour=True)

        for sensor in sensors:
            neighbors = [
                sensor.neighbour_name_1,
                sensor.neighbour_name_2,
                sensor.neighbour_name_3,
            ]

            if not all(neighbors):
                self.stdout.write(self.style.ERROR(f"❌ {sensor.name}: Missing one or more neighbors"))
                continue

            online_neighbors = [n for n in neighbors if n]

            if not online_neighbors:
                self.stdout.write(self.style.ERROR(f"❌ {sensor.name}: All neighbors are offline"))
                continue

            self.stdout.write(f"🔄 Processing {sensor.name} from {start_time} to {end_time}")

            current = start_time
            while current < end_time:
                window_start = current
                window_end = current + interval

                # Delete existing record if it exists
                deleted_count, _ = EnvironmentSensorRecord.objects.filter(
                    sensor=sensor,
                    last_entry_time__range=(window_start, window_end)
                ).delete()

                if deleted_count:
                    self.stdout.write(self.style.WARNING(
                        f"🗑️ Deleted existing record for {sensor.name} at {window_end}"
                    ))

                # Aggregate neighbor data
                aggregates = []
                for neighbor in online_neighbors:
                    agg = EnvironmentSensorRecord.objects.filter(
                        sensor=neighbor,
                        created_at__range=(window_start, window_end)
                    ).aggregate(temp=Avg("tempareture"), hum=Avg("humidity"))

                    if agg["temp"] is not None and agg["hum"] is not None:
                        aggregates.append(agg)

                if aggregates:
                    avg_temp = round(sum(a["temp"] for a in aggregates) / len(aggregates), 2)
                    avg_hum = round(sum(a["hum"] for a in aggregates) / len(aggregates), 2)

                    EnvironmentSensorRecord.objects.create(
                        sensor=sensor,
                        start_time=window_start,
                        end_time=window_end,
                        tempareture=avg_temp,
                        humidity=avg_hum,
                        last_entry_time=window_end,
                        update_from_neighbour=True
                    )

                    self.stdout.write(self.style.SUCCESS(
                        f"✅ Created new record from neighbors for {sensor.name} at {window_start} → {window_end}"
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ Skipped {sensor.name} at {window_start} (no neighbor data)"
                    ))

                current += interval

            self.stdout.write(self.style.SUCCESS(f"🎯 Finished {sensor.name}\n"))
