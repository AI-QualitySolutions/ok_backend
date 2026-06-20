import random
from datetime import datetime, timedelta
import pytz
from django.core.management.base import BaseCommand
from django.utils import timezone
from camera.models import Camera, GuardPresenceHistory


class Command(BaseCommand):
    help = 'Generate non-overlapping GuardPresenceHistory for all guard cameras from June 4, 12AM (Asia/Riyadh).'

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        start_base_time = riyadh_tz.localize(datetime(2025, 6, 6, 6, 0, 0))
        now = timezone.now().astimezone(riyadh_tz)

        cameras = Camera.objects.filter(type='guard')
        if not cameras.exists():
            self.stdout.write(self.style.ERROR("❌ No cameras with type='guard' found."))
            return


        total_created = 0
        

        for camera in cameras:
            
            camera_activate_check = GuardPresenceHistory.objects.filter(
                camera=camera
            ).order_by('-end_time').first()

            if camera_activate_check and camera_activate_check.end_time > timezone.now() - timedelta(minutes=10):
                self.stdout.write(self.style.WARNING(
                    f"⏭️ Skipping camera {camera.sn} — last record ends within 10 minutes"
                ))
                continue
            current_start = start_base_time
            created_count = 0
            number_insert = 0
            self.stdout.write(self.style.NOTICE(f"📹 Processing camera: {camera.sn}"))
            cutoff_time = now - timedelta(minutes=5)
            while current_start < cutoff_time:
                if number_insert > 18:
                    number_insert = 0
                    
                if number_insert < 15:
                    guard_count = random.randint(1, 3)
                    duration = random.randint(2, 10)
                    present = True
                else:
                    guard_count = random.randint(0, 4)
                    duration = random.randint(1, 4)
                    present = False

                    

                current_end = current_start + timedelta(minutes=duration)

                # Stop if end goes beyond now
                if current_end > now:
                    break
                # Check overlap
                exists = GuardPresenceHistory.objects.filter(
                    camera=camera,
                    start_time__lt=current_end,
                    end_time__gt=current_start
                ).exists()

                if exists:
                    self.stdout.write(self.style.WARNING(
                        f"⏭️  Skipped overlap: {camera.sn} at {current_start.strftime('%Y-%m-%d %H:%M')}"
                    ))
                else:
                    GuardPresenceHistory.objects.create(
                        camera=camera,
                        guard_count=guard_count,
                        present=present,
                        start_time=current_start,
                        end_time=current_end,
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ Created: {camera.sn} | Guards: {guard_count} | {current_start.strftime('%H:%M')} ➜ {current_end.strftime('%H:%M')}"
                    ))
                    created_count += 1
                    total_created += 1
                    number_insert += 1

                # Next session starts after this one ends
                current_start = current_end

            self.stdout.write(self.style.NOTICE(f"📊 Camera {camera.sn}: {created_count} entries created.\n"))

        self.stdout.write(self.style.SUCCESS(f"🎉 All done! Total records created: {total_created}"))
