from django.core.management.base import BaseCommand
from camera.models import Camera
from django.db import transaction

class Command(BaseCommand):
    help = "Rename Camera SNs based on their type"

    def handle(self, *args, **options):
        type_groups = {}

        # Group cameras by type
        for cam_type, _ in Camera.type_choices:
            type_groups[cam_type] = Camera.objects.filter(type=cam_type).order_by('id')

        with transaction.atomic():
            for cam_type, cameras in type_groups.items():
                for index, camera in enumerate(cameras, start=1):
                    new_sn = f"{cam_type}-{index}"
                    if camera.sn != new_sn:
                        self.stdout.write(f"Renaming {camera.sn} -> {new_sn}")
                        camera.sn = new_sn
                        camera.save()

        self.stdout.write(self.style.SUCCESS("All camera SNs renamed successfully."))
