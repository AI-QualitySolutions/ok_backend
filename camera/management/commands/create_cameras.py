import random
from django.core.management.base import BaseCommand
from faker import Faker
from camera.models import Camera
from datetime import datetime, timedelta
from django.utils import timezone
import pytz
from tent.models import Tent
import string


def generate_unique_sn(existing_sns):
    chars = string.ascii_uppercase + string.digits
    while True:
        sn = ''.join(random.choices(chars, k=random.choice([4, 5])))
        if sn not in existing_sns:
            existing_sns.add(sn)
            return sn


class Command(BaseCommand):
    help = "Generate 15 fake cameras per tent (3 per type)"

    def handle(self, *args, **options):
        fake = Faker()
        saudi_arabia_tz = pytz.timezone('Asia/Riyadh')

        # ['clean', 'guard', 'water', 'headcount', 'kitchen']
        camera_types = [choice[0] for choice in Camera.type_choices]
        tents = Tent.objects.all()

        if not tents.exists():
            self.stdout.write(self.style.ERROR(
                'No tents found in the database.'))
            return

        cameras_to_create = []
        start_date = datetime(2025, 5, 1, tzinfo=saudi_arabia_tz)
        end_date = datetime(2025, 12, 31, tzinfo=saudi_arabia_tz)
        generated_sns = set(Camera.objects.values_list('sn', flat=True))


        for tent in tents:
            for cam_type in camera_types:
                for i in range(3):  # 3 cameras per type
                    created_at = fake.date_time_between(
                        start_date=start_date, end_date=end_date)
                    created_at = saudi_arabia_tz.localize(created_at)

                    updated_at = created_at + \
                        timedelta(minutes=random.randint(1, 1440))
                    heart_beat_time = fake.date_time_between(
                        start_date=start_date, end_date=end_date)
                    heart_beat_time = saudi_arabia_tz.localize(heart_beat_time)

                    sn = generate_unique_sn(generated_sns)
                    camera = Camera.objects.create(
                        sn=str(sn),
                        tent=tent,
                        type=cam_type,
                        heart_beat_time=heart_beat_time,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    cameras_to_create.append(camera)
