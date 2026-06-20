from django.core.management.base import BaseCommand
from camera.models import Camera, CounterHistory
from django.utils.timezone import now
import random


class Command(BaseCommand):
    help = 'Pushes CounterHistory records for all cameras of type "peoplecount"'

    def handle(self, *args, **kwargs):
        cameras = Camera.objects.filter(type="peoplecount")

        if not cameras.exists():
            self.stdout.write(self.style.ERROR(
                "No cameras found with type 'peoplecount'."))
            return

        for camera in cameras:
            total_out = random.randint(1, 50)
            # ensures total_in >= total_out
            total_in = random.randint(total_out, 60)

            counter = CounterHistory.objects.create(
                camera=camera,
                sn=camera.sn,
                total_in=total_in,
                total_out=total_out,
                passby=random.randint(0, 10),
                turnback=random.randint(0, 10),
                avg_stay_time=random.randint(30, 300),
                in_adult=random.randint(0, 40),
                out_adult=random.randint(0, 40),
                passby_adult=random.randint(0, 5),
                turnback_adult=random.randint(0, 5),
                in_child=random.randint(0, 10),
                out_child=random.randint(0, 10),
                passby_child=random.randint(0, 3),
                turnback_child=random.randint(0, 3),
                total=random.randint(0, 100),
                start_time=now(),
                end_time=now(),
            )

            self.stdout.write(self.style.SUCCESS(
                f"CounterHistory pushed for camera {camera.sn} (ID: {camera.id})"
            ))
