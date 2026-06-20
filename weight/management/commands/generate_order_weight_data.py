from faker import Faker
from django.core.management.base import BaseCommand
from weight.models import OrderWeight, WeightConditions
from sensor.models import EnvironmentSensor
from datetime import datetime
from django.utils import timezone
import random
import pytz

riyadh_tz = pytz.timezone("Asia/Riyadh")


class Command(BaseCommand):
    help = 'Create fake order weights with ~1-1.5% rejection rate for dinner and 0% for breakfast/lunch for June 4, 2025, aligned with previous data'

    def handle(self, *args, **kwargs):
        fake = Faker()
        fixed_date = timezone.make_aware(datetime(2025, 6, 4))
        weight_sensors = list(EnvironmentSensor.objects.filter(type="weight"))
        print(weight_sensors)

        if not weight_sensors:
            self.stdout.write(self.style.ERROR("No weight sensors found"))
            return

        condition = WeightConditions.objects.order_by('-created_at').first()

        if not condition:
            self.stdout.write(self.style.ERROR("No WeightConditions found"))
            return

        # Meal setup: (meal name, count, start_time, end_time, accepted_weight, target_rejection_percentage)
        meal_configs = [
            ("breakfast", 2311, condition.breakfast_start,
             condition.breakfast_end, condition.breakfast_weight_accepted, 1.1),
            ("lunch", 3291, condition.lunch_start, condition.lunch_end,
             condition.lunch_weight_accepted, 1.2),
            ("dinner", 2080, condition.dinner_start, condition.dinner_end,
             condition.dinner_weight_accepted, 1.19),
        ]


        total_created = 0
        batch = []

        for meal_name, count, start_time, end_time, accepted_weight, target_rejection_percentage in meal_configs:


            # Define start and end datetime range for the meal
            start_dt = datetime.combine(
                fixed_date.date(), start_time).replace(tzinfo=riyadh_tz)
            end_dt = datetime.combine(
                fixed_date.date(), end_time).replace(tzinfo=riyadh_tz)

            print(OrderWeight.objects.all().first().created_at)

            print(start_dt, end_dt)

            # Count existing data and rejections for this meal
            existing_records = OrderWeight.objects.filter(
                created_at__range=(start_dt, end_dt))
            existing_count = existing_records.count()
            print(existing_count)
            existing_rejected = existing_records.filter(
                weight__lt=accepted_weight).count()

            if existing_count >= count:
                self.stdout.write(self.style.WARNING(
                    f"\u26A0️ Skipping {meal_name}, already has {existing_count}/{count} records."
                ))
                continue

            remaining_to_create = count - existing_count

            # Calculate target rejections based on meal-specific rejection percentage
            total_target_rejected = round(
                count * target_rejection_percentage / 100)

            # Adjust for existing rejections
            remaining_rejected_needed = max(
                0, total_target_rejected - existing_rejected)

            # For dinner, ensure rejection rate for new records stays within 1-1.5%; for breakfast/lunch, enforce 0%
            if meal_name == "dinner":
                min_rejected = max(0, round(remaining_to_create * 0.01))
                max_rejected = round(remaining_to_create * 0.015)
                rejected_count = min(
                    max(remaining_rejected_needed, min_rejected), max_rejected)
            else:
                rejected_count = 0  # Enforce 0% rejection for breakfast and lunch

            accepted_count = remaining_to_create - rejected_count

            rejection_indices = set()
            if rejected_count > 0:
                rejection_indices = set(random.sample(
                    range(remaining_to_create), rejected_count))

            for i in range(remaining_to_create):
                is_rejected = i in rejection_indices
                if is_rejected:
                    weight = round(accepted_weight - random.uniform(1, 5), 2)
                else:
                    weight = round(accepted_weight +
                                   random.uniform(0.1, 10), 2)

                random_time = fake.date_time_between_dates(
                    datetime_start=start_dt, datetime_end=end_dt)
                created_at = timezone.make_aware(random_time)
                weight_sensor = random.choice(weight_sensors)

                batch.append(OrderWeight(
                    device_num=weight_sensor.sn,
                    weight=weight,
                    date=fixed_date.date(),
                    is_modified=False,
                    secret=fake.uuid4(),
                    weight_sensor=weight_sensor,
                    created_at=created_at,
                    updated_at=created_at,
                ))
                total_created += 1

        # OrderWeight.objects.bulk_create(batch)
        self.stdout.write(self.style.SUCCESS(
            f"\u2705 Created {total_created} OrderWeight records for June 4, 2025"))
