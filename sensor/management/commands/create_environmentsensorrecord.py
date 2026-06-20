import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
import pytz
from sensor.models import EnvironmentSensorRecord, EnvironmentSensor
from utils.time import Current_saudi_time

class Command(BaseCommand):
    help = 'Generate EnvironmentSensorRecord entries for each EnvironmentSensor at 5-minute intervals from start_time to end_time (non-batch)'

    def handle(self, *args, **kwargs):
        tzinfo = pytz.UTC
        start_time, end_time = Current_saudi_time()

        sensors = EnvironmentSensor.objects.filter(check_neighbour=False)
        if not sensors.exists():
            self.stdout.write(self.style.WARNING('No EnvironmentSensor instances found. Aborting.'))
            return

        interval = timedelta(minutes=5)
        total_created = 0

        for sensor in sensors:
            current_time = start_time
            count = 0

            while current_time <= end_time:
                last_entry_time = current_time
                record_start = last_entry_time - interval
                record_end = last_entry_time + interval

                created_at = last_entry_time
                updated_at = created_at + timedelta(minutes=random.randint(1, 1440))

                # Nighttime: 6 PM - 6 AM
                if 18 <= updated_at.hour or updated_at.hour < 6:
                    temperature = int(random.uniform(28.0, 31.0) * 10)
                else:
                    temperature = int(random.uniform(40.0, 45.0) * 10)

                humidity = random.randint(25, 40)

                record = EnvironmentSensorRecord(
                    sensor=sensor,
                    tempareture=temperature,
                    humidity=humidity,
                    last_entry_time=last_entry_time,
                    start_time=record_start,
                    end_time=record_end,
                    created_at=created_at,
                    updated_at=updated_at
                )
                record.save()
                count += 1
                total_created += 1

                current_time += interval

            self.stdout.write(self.style.SUCCESS(f'Created {count} records for sensor ID {sensor.id}'))

        self.stdout.write(self.style.SUCCESS(f'🎉 Successfully created {total_created} records in total.'))
