from django.core.management.base import BaseCommand
from camera.models import BathroomMonitoringHistory

class Command(BaseCommand):
    help = 'Updates BathroomMonitoringHistory records based on is_annotated status'

    def handle(self, *args, **options):
        records = BathroomMonitoringHistory.objects.all()
        updated_count = 0

        for record in records:
            try:
                if record.is_annotated:
                    # Keep annotator_status as-is to trigger DB update
                    data = record.annotator_status
                    record.annotator_status = data

                else:
                    # Keep cleaner_count and present unchanged
                    count = record.cleaner_count
                    record.cleaner_count = count

                record.save()
                updated_count += 1
                self.stdout.write(f'Updated record ID {record.id}')
            except Exception as e:
                self.stderr.write(f'Error updating record ID {record.id}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} records'))
