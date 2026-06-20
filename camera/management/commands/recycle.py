from django.core.management.base import BaseCommand
from camera.models import RecycleMonitoringReport


class Command(BaseCommand):
    help = 'Updates RecycleMonitoringReport records based on is_annotated status'

    def handle(self, *args, **options):
        records = RecycleMonitoringReport.objects.all()
        updated_count = 0

        for record in records:
            try:
                if record.is_annotated:
                    data = record.annotator_status
                    record.annotator_status = data
                else:
                    data = record.is_clean
                    record.is_clean = data

                record.save()
                updated_count += 1
                self.stdout.write(f'Updated record ID {record.id}')
            except Exception as e:
                self.stderr.write(f'Error updating record ID {record.id}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} records'))
