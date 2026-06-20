import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord


class Command(BaseCommand):
    help = "Generate EnvironmentSensorRecord for each sensor using neighbor averages from 6 June 2025, 12:00 AM Riyadh time until now."

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        interval = timedelta(minutes=5)

        # Start and end time
        start_time = riyadh_tz.localize(datetime(2025, 6, 4, 0, 0, 0))
        end_time = timezone.now().astimezone(riyadh_tz)

        sensors = EnvironmentSensor.objects.filter(type="environment", check_neighbour=True)

        for sensor in sensors:
            neighbors = [
                sensor.neighbour_name_1,
                sensor.neighbour_name_2,
                sensor.neighbour_name_3,
            ]

            if not all(neighbors):
                continue

            online_neighbors = [n for n in neighbors if n and True]

            if not online_neighbors:
                continue

            count = 0
            pre_temperature = None
            current = start_time

            while current < end_time:
                window_start = current
                window_end = current + interval

                # Get existing record if any
                existing_record = EnvironmentSensorRecord.objects.filter(
                    sensor=sensor,
                    last_entry_time__range=(window_start, window_end)
                ).order_by('-last_entry_time').first()

                if existing_record:
                    if count == 0:
                        pre_temperature = existing_record.tempareture
                        count = 1
                    elif existing_record.tempareture == pre_temperature:
                        count += 1
                        if count == 12:
                            update_by_neighbour = True
                        else:
                            update_by_neighbour = False
                    else:
                        count = 1
                        pre_temperature = existing_record.tempareture
                        update_by_neighbour = False

                    if count < 12:
                        current += interval
                        continue
                else:
                    count = 0
                    update_by_neighbour = True  # No data, try to generate from neighbors

                # Calculate average from online neighbors
                aggregates = []
                for neighbor in online_neighbors:
                    agg = EnvironmentSensorRecord.objects.filter(
                        sensor=neighbor,
                        created_at__range=(window_start, window_end)
                    ).aggregate(temp=Avg("tempareture"), hum=Avg("humidity"))

                    if agg["temp"] is not None and agg["hum"] is not None:
                        aggregates.append(agg)

                if aggregates and update_by_neighbour:
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

                else:
                    pass

                current += interval

            self.stdout.write(self.style.SUCCESS(f"🎯 Finished {sensor.name}\n"))
