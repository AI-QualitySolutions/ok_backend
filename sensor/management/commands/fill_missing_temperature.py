import pytz
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from sensor.models import EnvironmentSensor, EnvironmentSensorRecord
from tent.models import Tent, Company


def get_duration_minutes(start, end):
    return (end - start).total_seconds() / 60


def create_data(sensor, temp, humidity, time):
    return EnvironmentSensorRecord.objects.create(
        sensor=sensor,
        tempareture=round(temp, 2),
        humidity=humidity,
        last_entry_time=time
    ).id


class Command(BaseCommand):
    help = "Fill missing EnvironmentSensorRecord data smoothly between 06:00 and 23:00 on 2025-06-06 with +0.75°C daily modulation"

    def handle(self, *args, **kwargs):
        tz = pytz.timezone('Asia/Riyadh')
        date = datetime(2025, 6, 6)
        start_time = tz.localize(datetime(date.year, date.month, date.day, 6, 0))
        end_time = tz.localize(datetime(date.year, date.month, date.day, 23, 0))
        midday = tz.localize(datetime(date.year, date.month, date.day, 12, 0))
        company = Company.objects.get(id=1)
        tents = Tent.objects.filter(company=company, is_arafa=False)
            
        sensors = EnvironmentSensor.objects.filter(tent__in=tents, type="environment")
        for sensor in sensors:
            env_records = EnvironmentSensorRecord.objects.filter(
                sensor=sensor,
                last_entry_time__gte=start_time,
                last_entry_time__lte=end_time
            ).order_by('last_entry_time')

            if not env_records.exists():
                continue

            prev = {}
            for record in env_records:
                if not prev:
                    prev["last_entry_time"] = record.last_entry_time
                    prev["temp"] = record.tempareture
                    prev["hum"] = record.humidity
                    continue

                gap_minutes = get_duration_minutes(prev["last_entry_time"], record.last_entry_time)
                if gap_minutes > 50:
                    total_steps = int(gap_minutes // 5)
                    time_step = prev["last_entry_time"]

                    for step in range(1, total_steps):
                        time_step += timedelta(minutes=5)
                        minutes_passed = get_duration_minutes(prev["last_entry_time"], time_step)

                        # Progress ratio within the gap
                        progress = minutes_passed / gap_minutes

                        # Linear temperature interpolation
                        temp = prev["temp"] + (record.tempareture - prev["temp"]) * progress

                        # Time-of-day-based smooth modulation
                        total_minutes_from_start = get_duration_minutes(start_time, time_step)
                        day_duration_minutes = get_duration_minutes(start_time, end_time)
                        day_progress = total_minutes_from_start / day_duration_minutes

                        modulation_strength = 3.0  # max added temp at midday
                        if time_step < midday:
                            temp += modulation_strength * day_progress  # morning rise
                        else:
                            temp += modulation_strength * (1 - day_progress)  # afternoon fall

                        # Humidity linear interpolation
                        humidity = int(prev["hum"] + (record.humidity - prev["hum"]) * progress)

                        create_data(sensor, temp, humidity, time_step)

                # Update for next iteration
                prev["last_entry_time"] = record.last_entry_time
                prev["temp"] = record.tempareture
                prev["hum"] = record.humidity

            self.stdout.write(self.style.SUCCESS(f"✔ Gaps filled for sensor: {sensor.sn}"))

        self.stdout.write(self.style.SUCCESS("✅ All sensors processed successfully."))





# from django.db.models import F, ExpressionWrapper, DurationField
# from django.db.models.functions import Now


# import random
# import pytz
# from datetime import datetime, timedelta
# from django.core.management.base import BaseCommand
# from sensor.models import EnvironmentSensor, EnvironmentSensorRecord


# def get_duration_minutes(start, end):
#     delta = end - start
#     return delta.total_seconds() / 60


# def create_data(sensor, temp, humidity, time):
#     record = EnvironmentSensorRecord.objects.create(
#         sensor=sensor,
#         tempareture=round(temp, 2),
#         humidity=humidity,
#         last_entry_time=time
#     )

#     return record.id


# class Command(BaseCommand):
#     help = "Fill missing EnvironmentSensorRecord data between 06:00 and 23:00 on 2025-06-06"

#     def handle(self, *args, **kwargs):
#         tz = pytz.timezone('Asia/Riyadh')
#         start_time = tz.localize(datetime(2025, 6, 6, 6, 0))
#         end_time = tz.localize(datetime(2025, 6, 6, 23, 0))
#         sensors = EnvironmentSensor.objects.filter(tent__id=95)
#         for sensor in sensors:
#             env_records = EnvironmentSensorRecord.objects.filter(
#                 sensor=sensor,
#                 last_entry_time__gte=start_time,
#                 last_entry_time__lte=end_time
#             ).order_by('last_entry_time')
            
#             prev = {}
#             for record in env_records[:]:
#                 if not prev:
#                     prev["last_entry_time"] = record.last_entry_time
#                     prev["temp"] = record.tempareture
#                     prev["hum"] = record.humidity
#                 elif get_duration_minutes(
#                     prev["last_entry_time"], record.last_entry_time) > 50:
#                     prev_time = prev["last_entry_time"]
#                     next_time = record.last_entry_time
#                     prev_temp = prev["temp"]
#                     next_temp = record.tempareture
#                     prev_hum = prev["hum"]
#                     next_hum = record.humidity
#                     while get_duration_minutes(prev_time, next_time) > 6:
#                         prev_time = prev_time + timedelta(minutes=5)
#                         next_time = next_time - timedelta(minutes=5)
#                         prev_temp = round(random.uniform(-0.5, 0.5), 2) + round(prev_temp, 2)
#                         next_temp = round(random.uniform(-0.5, 0.5), 2) + round(next_temp, 2)
#                         prev_value = create_data(
#                             record.sensor, prev_temp, prev_hum, prev_time)
#                         next_value = create_data(
#                             record.sensor, next_temp, next_hum, next_time)

#                     prev = {}
            
#             self.stdout.write(self.style.SUCCESS(f"Filled gaps for sensor: {sensor.sn}"))
#         self.stdout.write(self.style.SUCCESS("✅ Data gap filling complete for all sensors."))

#         return None

#     # morning_temp = 27.02
#     # noon_temp = 31.0
#     # evening_temp = 27.02

#     # if not sensor:
#     #     self.stdout.write("Sensor with ID 1573 not found.")
#     #     return

#     # total_minutes = int((end_time - start_time).total_seconds() // 60)
#     # total_steps = total_minutes // 6

#     # for step in range(total_steps + 1):
#     #     # Calculate current time
#     #     base_time = start_time + timedelta(minutes=step * 6)

#     #     # Add random seconds and milliseconds
#     #     random_seconds = random.randint(0, 59)
#     #     random_microseconds = random.randint(0, 999999)
#     #     current_time = base_time.replace(
#     #         second=random_seconds,
#     #         microsecond=random_microseconds
#     #     )

#     #     # Calculate progression of day for sine wave
#     #     progress = step / total_steps
#     #     temp = morning_temp + (noon_temp - morning_temp) * \
#     #         math.sin(math.pi * progress)
#     #     humidity = 60 + 15 * math.sin(math.pi * progress)

#     #     # Add noise
#     #     temp += random.uniform(-0.2, 0.2)
#     #     humidity += random.randint(-2, 2)

#     #     # Round and clamp
#     #     temp = round(temp, 2)
#     #     humidity = max(30, min(100, int(humidity)))

#     #     # Skip if record already exists
#     #     if not EnvironmentSensorRecord.objects.filter(sensor=sensor, last_entry_time=current_time).exists():
#     #         record = EnvironmentSensorRecord.objects.create(
#     #             sensor=sensor,
#     #             tempareture=temp,
#     #             humidity=humidity,
#     #             last_entry_time=current_time
#     #         )
#     #         print(
#     #             f"Inserted record at {current_time.isoformat()} — Temp: {temp}, Humidity: {humidity}")

#     # self.stdout.write(self.style.SUCCESS(
#     #     "Missing data filled successfully."))
