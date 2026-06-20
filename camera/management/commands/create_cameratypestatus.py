from django.core.management.base import BaseCommand
from camera.models import CameraType, CameraStatus


class Command(BaseCommand):
    help = "Seeds camera types and their statuses"

    def handle(self, *args, **kwargs):
        data = {
            "guard": ["absent", "1", "2", "3", "4", "5", "6", "7", "8"],
            "kitchen": ["no_gloves", "no_masks", "no_hats", "garbage", "food_uncovered", "uniform_missing"],
            "garbage": ["garbage", "clean"],
            "recycle": ["recycle", "clean"],
            "buffet": ["no_waiter", "food_empty", "waiter_without_precaution", "crowd", "garbage", "dirty_plate", "not_enough_food", "empty_container"],
            "bathroom": ["absent", "1", "2", "3", "4", "5", "6", "7", "8"],
            "sentiment": ["very_sad", "sad", "neutral", "happy", "very_happy"],
            "peoplecount": []
        }

        for type_name, statuses in data.items():
            camera_type, created = CameraType.objects.get_or_create(
                type=type_name)
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"Created CameraType: {type_name}"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"CameraType already exists: {type_name}"))

            for status in statuses:
                if status:  # Skip empty string if it's not meaningful
                    camera_status, created = CameraStatus.objects.get_or_create(
                        name=status,
                        type=camera_type
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(
                            f"  - Added status: '{status}' to type: '{type_name}'"))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"  - Status already exists: '{status}' for type: '{type_name}'"))
