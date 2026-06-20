# File: yourapp/management/commands/generate_missing_weights.py

import random
from datetime import datetime, timedelta
import pytz

from django.core.management.base import BaseCommand
from tent.models import Tent
from sensor.models import EnvironmentSensor
from weight.models import OrderWeight, WeightConditions


class Command(BaseCommand):
    help = 'Generate missing weight entries for multiple tents based on weight conditions'

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        fixed_date = riyadh_tz.localize(datetime(2025, 6, 4))

        # Select the closest weight condition
        weight_condition = (
            WeightConditions.objects.filter(created_at__date=fixed_date.date()).first() or
            WeightConditions.objects.filter(created_at__lte=fixed_date).order_by('-end_date').first() or
            WeightConditions.objects.filter(created_at__gte=fixed_date).order_by('start_date').first()
        )

        if not weight_condition:
            self.stdout.write(self.style.ERROR("❌ No WeightConditions found for the selected date."))
            return

        tent_meal_totals = [
        {
            "id": 7,
            "breakfast": 0,
            "lunch": 0,
            "dinner": 78
        },
        {
            "id": 8,
            "breakfast": 2892,
            "lunch": 2904,
            "dinner": 1060
        },
        {
            "id": 30,
            "breakfast": 2311,
            "lunch": 3291,
            "dinner": 2080
        },
        {
            "id": 31,
            "breakfast": 892,
            "lunch": 904,
            "dinner": 1204
        },
        {
            "id": 32,
            "breakfast": 451,
            "lunch": 783,
            "dinner": 863
        },
        {
            "id": 33,
            "breakfast": 400,
            "lunch": 300,
            "dinner": 0
        },
        {
            "id": 34,
            "breakfast": 0,
            "lunch": 209,
            "dinner": 990
        },
        {
            "id": 35,
            "breakfast": 0,
            "lunch": 0,
            "dinner": 438
        },
        {
            "id": 36,
            "breakfast": 123,
            "lunch": 543,
            "dinner": 2334
        },
        {
            "id": 37,
            "breakfast": 0,
            "lunch": 251,
            "dinner": 2749
        },
        {
            "id": 38,
            "breakfast": 0,
            "lunch": 220,
            "dinner": 1435
        }
        ]

        meal_names = ['breakfast', 'lunch', 'dinner']

        for tent_data in tent_meal_totals:
            tent_id = tent_data['id']
            tent = Tent.objects.filter(name=tent_id, company__id=1, is_arafa=False).first()
            if not tent:
                self.stdout.write(self.style.ERROR(f"❌ Tent with name {tent_id} not found. Skipping..."))
                continue

            sensors = EnvironmentSensor.objects.filter(tent=tent, type='weight')
            if not sensors.exists():
                self.stdout.write(self.style.ERROR(f"❌ No weight sensors found for tent {tent.name} (ID {tent_id}). Skipping..."))
                continue

            for sensor in sensors:
                for meal_name in meal_names:
                    expected_total = tent_data.get(meal_name, 0)
                    if expected_total <= 0:
                        self.stdout.write(self.style.WARNING(
                            f"⚠️ Skipping {meal_name} for Tent {tent_id} due to zero or negative expected total"))
                        continue

                    start_attr = f"{meal_name.lower()}_start"
                    end_attr = f"{meal_name.lower()}_end"
                    weight_attr = f"{meal_name.lower()}_weight_accepted"

                    start_time = riyadh_tz.localize(datetime.combine(fixed_date.date(), getattr(weight_condition, start_attr)))
                    end_time = riyadh_tz.localize(datetime.combine(fixed_date.date(), getattr(weight_condition, end_attr)))
                    target_weight = getattr(weight_condition, weight_attr) or 0

                    existing_count = OrderWeight.objects.filter(
                        weight_sensor=sensor,
                        created_at__range=(start_time, end_time),
                        is_deleted=False
                    ).count()

                    to_create = max(expected_total - existing_count, 0)

                    self.stdout.write(self.style.WARNING(
                        f"🔍 Tent {tent_id} - {meal_name} - Sensor: {sensor.sn} - Existing: {existing_count}, To Create: {to_create}"
                    ))

                    if to_create > 0:
                        entries = []
                        interval = (end_time - start_time) / to_create
                        counter = 0

                        for i in range(to_create):
                            offset = timedelta(seconds=random.randint(0, 60))
                            timestamp = min(start_time + i * interval + offset, end_time - timedelta(seconds=1))

                            if counter > random.randint(75, 90):
                                weight = round(random.uniform(target_weight - 100.5, target_weight - 50.5), 2)
                                counter = 0
                            else:
                                weight = round(random.uniform(target_weight + 0.5, target_weight + 50.5), 2)
                                counter += 1

                            entries.append(OrderWeight(
                                device_num=sensor.sn,
                                weight=weight,
                                date=timestamp,
                                created_at=timestamp,
                                weight_sensor=sensor
                            ))

                        OrderWeight.objects.bulk_create(entries)

                        self.stdout.write(self.style.SUCCESS(
                            f"✅ Created {to_create} weights for Tent {tent_id} - {meal_name} - Sensor {sensor.sn}"
                        ))

                        final_count = OrderWeight.objects.filter(
                            weight_sensor=sensor,
                            created_at__range=(start_time, end_time),
                            is_deleted=False
                        ).count()

                        self.stdout.write(self.style.SUCCESS(
                            f"📊 Tent {tent_id} - Final count for {meal_name}: {final_count} (Expected: {expected_total})"
                        ))

        self.stdout.write(self.style.SUCCESS("🎉 All missing weights generated successfully."))
