from django.core.management.base import BaseCommand
from datetime import datetime
import pytz
from sensor.models import EnvironmentSensorRecord
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed


class Command(BaseCommand):
    help = 'Multithreaded update of EnvironmentSensorRecord'

    BATCH_SIZE = 10000
    THREADS = 5  # You can tune this based on your CPU

    def handle(self, *args, **kwargs):
        riyadh_tz = pytz.timezone("Asia/Riyadh")
        date = riyadh_tz.localize(datetime(2025, 6, 6, 0, 0, 0))

        # Get all relevant record IDs
        record_ids = list(
            EnvironmentSensorRecord.objects.filter(
                update_from_neighbour=False, sensor__tent__is_arafa=False
            ).order_by('id').values_list('id', flat=True)
        )

        total = len(record_ids)
        self.stdout.write(f"Total records to process: {total}")

        # Split into chunks
        chunks = [record_ids[i:i + self.BATCH_SIZE]
                  for i in range(0, total, self.BATCH_SIZE)]

        updated_count = 0

        with ThreadPoolExecutor(max_workers=self.THREADS) as executor:
            futures = [executor.submit(self.process_chunk, chunk)
                       for chunk in chunks]

            for future in as_completed(futures):
                updated_count += future.result()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Updated {updated_count} EnvironmentSensorRecord(s) using multithreading."
        ))

    def process_chunk(self, chunk_ids):
        buffer = []
        count = 0
        records = EnvironmentSensorRecord.objects.filter(id__in=chunk_ids)

        for record in records:
            if record.last_entry_time:
                time_diff = abs(
                    (record.last_entry_time - record.created_at).total_seconds()
                )
                if time_diff > 300:
                    record.last_entry_time = record.created_at
                    record.update_from_neighbour = False
                    buffer.append(record)

        if buffer:
            with transaction.atomic():
                EnvironmentSensorRecord.objects.bulk_update(
                    buffer, ['last_entry_time', 'update_from_neighbour'], batch_size=len(buffer)
                )
                count = len(buffer)

        return count
