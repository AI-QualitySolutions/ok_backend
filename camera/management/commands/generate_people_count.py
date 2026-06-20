import random
from datetime import datetime, timedelta
import pytz
from django.core.management.base import BaseCommand
from django.db.models import Sum
from camera.models import Camera, CounterHistory
from tent.models import Tent


class Command(BaseCommand):
    help = 'Simulate gradual people reduction from 4:00 AM to 8:00 AM for each tent camera, ending with ~30–50 people.'

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        range_start = riyadh_tz.localize(datetime(2025, 6, 5, 4, 0, 0))
        range_end = riyadh_tz.localize(datetime(2025, 6, 5, 8, 0, 0))
        interval = timedelta(minutes=5)
        total_intervals = int((range_end - range_start).total_seconds() // 300)  # 5-minute intervals

        tents = Tent.objects.all()

        for tent in tents:
            cameras = Camera.objects.filter(tent=tent, type="peoplecount")
            if not cameras:
                self.stdout.write(self.style.WARNING(f"⚠️ No camera for Tent '{tent.name}'. Skipping."))
                continue

            # Calculate people inside before 8:00 AM
            previous_entries = CounterHistory.objects.filter(
                camera__in=cameras,
                end_time__lte=range_end
            )
            camera = cameras.first()
            total_in = previous_entries.aggregate(Sum("total_in"))["total_in__sum"] or 0
            total_out = previous_entries.aggregate(Sum("total_out"))["total_out__sum"] or 0
            initial_people = total_in - total_out


            if initial_people <= 0:
                self.stdout.write(self.style.WARNING(f"🏕 Tent '{tent.name}' has no people before 8:00 AM. Skipping."))
                continue

            target_people = random.randint(30, 50)
            to_leave = initial_people - target_people

            if to_leave <= 0:
                self.stdout.write(self.style.WARNING(f"🔕 Tent '{tent.name}' already at target level. No action taken."))
                continue

            per_interval_leave = to_leave // total_intervals
            remainder = to_leave % total_intervals

            current_time = range_start
            people_inside = initial_people
            entries = []
            total_in_this = 0
            total_out_this = 0

            for i in range(total_intervals):
                next_time = current_time + interval

                # Natural-looking exit pattern with fluctuation
                leave_now = per_interval_leave + (1 if i < remainder else 0)
                leave_now += random.randint(-2, 2)
                leave_now = max(0, min(leave_now, people_inside))

                in_now = random.randint(0, 2)  # simulate minimal inflow
                total_in_this += in_now
                total_out_this += leave_now

                # Update current count
                people_inside += in_now - leave_now

                entries.append(CounterHistory(
                    camera=camera,
                    sn=camera.sn,
                    total_in=in_now,
                    total_out=leave_now,
                    start_time=current_time,
                    end_time=next_time
                ))

                current_time = next_time

            # Final adjustment if people count isn't exactly target
            final_people = people_inside
            if final_people != target_people:
                adjustment = final_people - target_people
                entries.append(CounterHistory(
                    camera=camera,
                    sn=camera.sn,
                    total_in=0 if adjustment > 0 else abs(adjustment),
                    total_out=adjustment if adjustment > 0 else 0,
                    start_time=current_time,
                    end_time=current_time + interval
                ))
                self.stdout.write(self.style.WARNING(f"⚙️ Final adjustment of {adjustment} applied."))

            # Bulk save
            CounterHistory.objects.bulk_create(entries)
            

            self.stdout.write(self.style.SUCCESS(
                f"✅ {len(entries)} | initial_people: {initial_people} | entries created for {camera.sn} | Final people inside: {target_people} | Total in: {total_in_this} | Total out: {total_out_this}"
            ))

        self.stdout.write(self.style.SUCCESS("🎉 All tents processed successfully."))
