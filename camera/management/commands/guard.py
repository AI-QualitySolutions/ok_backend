from django.core.management.base import BaseCommand
from camera.models import GuardPresenceHistory

class Command(BaseCommand):
    help = 'Updates GuardPresenceHistory records based on is_annotated status'

    def handle(self, *args, **options):
        # Get all GuardPresenceHistory records
        records = GuardPresenceHistory.objects.all()
        updated_count = 0

        for record in records:
            try:
                if record.is_annotated:
                    data = record.annotator_status
                    record.annotator_status = data
                else:
                    data = record.guard_count
                    record.guard_count = data
                
                record.save()
                updated_count += 1
                self.stdout.write(f'Updated record ID {record.id}')
            except Exception as e:
                self.stderr.write(f'Error updating record ID {record.id}: {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} records'))