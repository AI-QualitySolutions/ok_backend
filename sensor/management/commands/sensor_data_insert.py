import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict


class Command(BaseCommand):
    help = "Generate EnvironmentSensorRecord for each sensor using neighbor averages from 4 June 2025, 12:00 AM Riyadh time until now."

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        interval = timedelta(minutes=5)

        # Start and end time
        start_time = riyadh_tz.localize(datetime(2025, 6, 4, 0, 0, 0))
        end_time = timezone.now().astimezone(riyadh_tz)

        sensors = EnvironmentSensor.objects.filter(type="environment", check_neighbour=True)

        with ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(lambda s: self.process_sensor(s, start_time, end_time, interval), sensors)

    def process_sensor(self, sensor, start_time, end_time, interval):
        neighbors = [sensor.neighbour_name_1, sensor.neighbour_name_2, sensor.neighbour_name_3]
        if not all(neighbors):
            return

        online_neighbors = [n for n in neighbors if n]
        if not online_neighbors: 
            return

        # Preload neighbor records to minimize DB hits
        neighbor_records = defaultdict(list)
        for neighbor in online_neighbors:
            records = EnvironmentSensorRecord.objects.filter(
                sensor=neighbor,
                created_at__range=(start_time, end_time)
            ).values("sensor_id", "created_at", "tempareture", "humidity")
            for rec in records:
                neighbor_records[neighbor.id].append(rec)

        current = start_time
        count = 0
        pre_temperature = None
        new_records = []

        while current < end_time:
            window_start = current
            window_end = current + interval

            existing_record = EnvironmentSensorRecord.objects.filter(
                sensor=sensor,
                last_entry_time__range=(window_start, window_end)
            ).order_by("-last_entry_time").first()

            if existing_record:
                if count == 0:
                    pre_temperature = existing_record.tempareture
                    count = 1
                elif existing_record.tempareture == pre_temperature:
                    count += 1
                    update_by_neighbour = count == 12
                else:
                    count = 1
                    pre_temperature = existing_record.tempareture
                    update_by_neighbour = False

                if count < 12:
                    current += interval
                    continue
            else:
                count = 0
                update_by_neighbour = True

            aggregates = []
            for neighbor in online_neighbors:
                records = [
                    r for r in neighbor_records[neighbor.id]
                    if window_start <= r["created_at"] < window_end
                ]
                if records:
                    temps = [r["tempareture"] for r in records if r["tempareture"] is not None]
                    hums = [r["humidity"] for r in records if r["humidity"] is not None]
                    if temps and hums:
                        avg_temp = sum(temps) / len(temps)
                        avg_hum = sum(hums) / len(hums)
                        aggregates.append((avg_temp, avg_hum))

            if aggregates and update_by_neighbour:
                avg_temp = round(sum(t for t, _ in aggregates) / len(aggregates), 2)
                avg_hum = round(sum(h for _, h in aggregates) / len(aggregates), 2)

                new_records.append(EnvironmentSensorRecord(
                    sensor=sensor,
                    start_time=window_start,
                    end_time=window_end,
                    tempareture=avg_temp,
                    humidity=avg_hum,
                    last_entry_time=window_end,
                    update_from_neighbour=True
                ))

            current += interval

        if new_records:
            EnvironmentSensorRecord.objects.bulk_create(new_records, batch_size=100)

        print(f"🎯 Finished {sensor.name}")
