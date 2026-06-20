from django.core.management.base import BaseCommand


import random
from datetime import datetime

from django.utils import timezone
from faker import Faker

from authentication.models import Company, MyUser
from tent.models import Tent

username = "kfrawee"
user = MyUser.objects.get(username=username)
company = Company.objects.get(id=1)


n = 10
faker = Faker()
tz = timezone.get_current_timezone()


class Command(BaseCommand):
    # TODO: Accept args
    def handle(self, *args, **kwargs):
        for i in range(n):
            is_arafa = random.choice([True, False])

            if is_arafa:
                longitude, latitude = (39.9635, 21.3651)
                location = faker.street_address() + ", Arafat"
                capacity = random.randint(1000, 5000)
                max_temp = round(random.uniform(22.0, 32.0), 2)
                avg_temp = round(random.uniform(20.0, 30.0), 2)
                min_temp = round(random.uniform(18.0, 28.0), 2)
                max_humidity = round(random.uniform(50.0, 70.0), 2)
                avg_humidity = round(random.uniform(45.0, 65.0), 2)
                min_humidity = round(random.uniform(40.0, 60.0), 2)
            else:
                longitude, latitude = (39.8579, 21.3891)
                location = faker.street_address() + ", Makkah"
                capacity = random.randint(0, 2000)
                max_temp = round(random.uniform(20.0, 30.0), 2)
                avg_temp = round(random.uniform(18.0, 28.0), 2)
                min_temp = round(random.uniform(15.0, 25.0), 2)
                max_humidity = round(random.uniform(40.0, 60.0), 2)
                avg_humidity = round(random.uniform(35.0, 55.0), 2)
                min_humidity = round(random.uniform(30.0, 50.0), 2)

            air_condition_update_time_naive = faker.date_time_between(
                start_date=datetime(2024, 1, 1, tzinfo=tz),
                end_date=datetime(2025, 12, 31, tzinfo=tz),
            )
            air_condition_update_time = timezone.make_aware(
                air_condition_update_time_naive, timezone=tz
            )

            Tent.objects.create(
                company=company,
                name=f"Tent {str(i+1).zfill(2)}",
                longitude=longitude,
                latitude=latitude,
                location=location,
                map_image=None,
                created_by=user,
                air_condition=random.randint(16, 30),
                air_condition_update_time=air_condition_update_time,
                capacity=capacity,
                is_arafa=is_arafa,
                adjust=random.randint(0, 90),
                fixed=faker.boolean(),
                max_adjust_tempareture=max_temp,
                avg_adjust_tempareture=avg_temp,
                min_adjust_tempareture=min_temp,
                is_adjust_tempareture=faker.boolean(),
                max_adjust_humidity=max_humidity,
                avg_adjust_humidity=avg_humidity,
                min_adjust_humidity=min_humidity,
                is_adjust_humidity=faker.boolean(),
            )
