import random
from django.core.management.base import BaseCommand
from faker import Faker
from camera.models import CameraHeartbeat, Camera
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

class Command(BaseCommand):
    help = 'Generate fake camera heartbeat data with created_at and updated_at in Saudi Arabia timezone for 2024-2025'

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Define the timezone for Saudi Arabia
        saudi_arabia_tz = pytz.timezone('Asia/Riyadh')

        # Define the start_date and end_date for the data range
        start_date = datetime(2025, 5, 1, tzinfo=saudi_arabia_tz)
        end_date = datetime(2025, 12, 31, tzinfo=saudi_arabia_tz)

        # Fetch all cameras to generate data for
        cameras = Camera.objects.all()

        if not cameras:
            self.stdout.write(self.style.WARNING('No cameras found in the database. Please add cameras first.'))
            return

        # Generate fake data for CameraHeartbeat
        for camera in cameras:
            # Generate data for one heartbeat per camera
            sn = camera.sn
            version = random.randint(1, 5)  # Random version number between 1 and 5
            mac_address = fake.mac_address()
            ip_address = fake.ipv4()
            connection_type = random.choice(['WIFI', 'LAN'])
            ip_address_method = random.choice(['DHCP', 'Dynamic'])
            host_name = fake.hostname()
            time_zone = random.randint(-12, 14)  # Random timezone between -12 and +14
            hw_platform = random.choice(['V4.0', 'V4.1', 'V4.2'])
            report_date = fake.date_this_year()

            # Generate time for heartbeat within the 2024-2025 range and make it timezone-aware for Saudi Arabia
            time = fake.date_time_between(start_date=start_date, end_date=end_date)
            time = saudi_arabia_tz.localize(time)  # Make the time timezone-aware (in Asia/Riyadh timezone)

            # Manually set created_at (naive datetime)
            created_at = fake.date_time_between(start_date=start_date, end_date=end_date)
            created_at = saudi_arabia_tz.localize(created_at)  # Ensure created_at is timezone-aware

            # Generate updated_at by adding a random timedelta to created_at
            # Ensure updated_at is later than created_at
            random_delta = timedelta(minutes=random.randint(1, 1440))  # Random delta between 1 minute and 24 hours
            updated_at = created_at + random_delta

            # Create the fake CameraHeartbeat entry
            CameraHeartbeat.objects.create(
                camera=camera,
                sn=sn,
                version=version,
                mac_address=mac_address,
                ip_address=ip_address,
                connection_type=connection_type,
                ip_address_method=ip_address_method,
                host_name=host_name,
                time_zone=time_zone,
                hw_platform=hw_platform,
                report_date=report_date,
                time=time,  # Now timezone-aware
                created_at=created_at,  # Manually set created_at (timezone-aware)
                updated_at=updated_at   # Manually set updated_at (timezone-aware)
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated fake camera heartbeat data with created_at and updated_at in Saudi Arabia timezone for 2024-2025.'))
