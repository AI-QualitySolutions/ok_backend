import random
from django.core.management.base import BaseCommand
from faker import Faker
from tent.models import Tent
from authentication.models import MyUser, Company
from django.utils.timezone import get_current_timezone, make_aware
from datetime import datetime


class Command(BaseCommand):
    help = "Ensure each company has at least 50 Tent records"

    def handle(self, *args, **kwargs):
        fake = Faker()
        users = MyUser.objects.all()
        companies = Company.objects.all()
        tz = get_current_timezone()

        if not users.exists():
            self.stdout.write(self.style.ERROR(
                'No users found in the database.'))
            return

        if not companies.exists():
            self.stdout.write(self.style.ERROR(
                'No companies found in the database.'))
            return

        for company in companies:
            current_count = Tent.objects.filter(company=company).count()
            needed = random.randint(2,5)

            if needed <= 0:
                self.stdout.write(self.style.NOTICE(
                    f"{company.name} already has {current_count} tents. Skipping."))
                continue

            for _ in range(needed):
                is_arafa = random.choice([True, False])

                if is_arafa:
                    longitude, latitude = (39.9635, 21.3651)
                    location = fake.street_address() + ", Arafat"
                    capacity = random.randint(1000, 5000)
                    max_temp = round(random.uniform(22.0, 32.0), 2)
                    avg_temp = round(random.uniform(20.0, 30.0), 2)
                    min_temp = round(random.uniform(18.0, 28.0), 2)
                    max_humidity = round(random.uniform(50.0, 70.0), 2)
                    avg_humidity = round(random.uniform(45.0, 65.0), 2)
                    min_humidity = round(random.uniform(40.0, 60.0), 2)
                else:
                    longitude, latitude = (39.8579, 21.3891)
                    location = fake.street_address() + ", Makkah"
                    capacity = random.randint(0, 2000)
                    max_temp = round(random.uniform(20.0, 30.0), 2)
                    avg_temp = round(random.uniform(18.0, 28.0), 2)
                    min_temp = round(random.uniform(15.0, 25.0), 2)
                    max_humidity = round(random.uniform(40.0, 60.0), 2)
                    avg_humidity = round(random.uniform(35.0, 55.0), 2)
                    min_humidity = round(random.uniform(30.0, 50.0), 2)

                air_condition_update_time_naive = fake.date_time_between(
                    start_date=datetime(2024, 1, 1, tzinfo=tz),
                    end_date=datetime(2025, 12, 31, tzinfo=tz),
                )
                air_condition_update_time = make_aware(
                    air_condition_update_time_naive, timezone=tz)
                count = Tent.objects.all().count()
                Tent.objects.create(
                    company=company,
                    name=f"Tent {count + 1}",
                    longitude=longitude,
                    latitude=latitude,
                    location=location,
                    map_image=None,
                    created_by=random.choice(users),
                    air_condition=random.randint(16, 30),
                    air_condition_update_time=air_condition_update_time,
                    capacity=capacity,
                    is_arafa=is_arafa,
                    adjust=random.randint(0, 90),
                    fixed=fake.boolean(),
                    max_adjust_tempareture=max_temp,
                    avg_adjust_tempareture=avg_temp,
                    min_adjust_tempareture=min_temp,
                    is_adjust_tempareture=fake.boolean(),
                    max_adjust_humidity=max_humidity,
                    avg_adjust_humidity=avg_humidity,
                    min_adjust_humidity=min_humidity,
                    is_adjust_humidity=fake.boolean(),
                )

            self.stdout.write(self.style.SUCCESS(
                f"Added {needed} tents to {company.name} (now has 50)."
            ))
