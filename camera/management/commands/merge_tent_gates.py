"""
Management command to merge a split tent pair (e.g. "48-1" / "48-2") into one
tent with two TentGate records.

Usage:
    python manage.py merge_tent_gates --tent1 "48-1" --tent2 "48-2" --merged-name "48"

What it does:
  1. Rename tent1 to merged_name (keeps all its cameras on Gate 1).
  2. Create TentGate records: "Gate 1" (tent1 cameras) and "Gate 2" (tent2 cameras).
  3. Move all cameras from tent2 → tent1, assigning them to Gate 2.
  4. Sum the capacities of both tents into the merged tent.
  5. Delete the now-empty tent2.

All CounterHistory records are untouched — they follow their cameras automatically.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from tent.models import Tent, TentGate
from camera.models import Camera


class Command(BaseCommand):
    help = 'Merge two half-tent records (split by gate) into one tent with two TentGate entries.'

    def add_arguments(self, parser):
        parser.add_argument('--tent1-id', required=True, type=int, dest='tent1_id', help='ID of the primary tent (Gate 1)')
        parser.add_argument('--tent2-id', required=True, type=int, dest='tent2_id', help='ID of the secondary tent to merge in (Gate 2)')
        parser.add_argument('--merged-name', required=True, dest='merged_name', help='Final name for the merged tent (e.g. "Center 48")')
        parser.add_argument('--gate1-name', default='Gate 1', dest='gate1_name', help='Label for the first gate (default: "Gate 1")')
        parser.add_argument('--gate2-name', default='Gate 2', dest='gate2_name', help='Label for the second gate (default: "Gate 2")')
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', help='Preview changes without saving')
        parser.add_argument('--list', action='store_true', dest='list_tents', help='List all tents with their IDs and exit')

    def handle(self, *args, **options):
        if options['list_tents']:
            self.stdout.write('\nAll tents (id | company | name):')
            for t in Tent.objects.select_related('company').order_by('company__name', 'name'):
                company = t.company.name if t.company else '—'
                self.stdout.write(f'  {t.id:>5}  {company:<30}  {t.name}')
            return

        tent1_id    = options['tent1_id']
        tent2_id    = options['tent2_id']
        merged_name = options['merged_name']
        gate1_name  = options['gate1_name']
        gate2_name  = options['gate2_name']
        dry_run     = options['dry_run']

        try:
            tent1 = Tent.objects.select_related('company').get(pk=tent1_id)
        except Tent.DoesNotExist:
            raise CommandError(f'Tent with id={tent1_id} not found. Use --list to see all tents.')

        try:
            tent2 = Tent.objects.select_related('company').get(pk=tent2_id)
        except Tent.DoesNotExist:
            raise CommandError(f'Tent with id={tent2_id} not found. Use --list to see all tents.')

        if tent1.company_id != tent2.company_id:
            raise CommandError('Both tents must belong to the same company.')

        cameras1 = list(Camera.objects.filter(tent=tent1, type='peoplecount'))
        cameras2 = list(Camera.objects.filter(tent=tent2, type='peoplecount'))

        self.stdout.write(f'\nPlan:')
        self.stdout.write(f'  Rename "{tent1.name}" → "{merged_name}"')
        self.stdout.write(f'  Merged capacity: {tent1.capacity} + {tent2.capacity} = {tent1.capacity + tent2.capacity}')
        self.stdout.write(f'  Create TentGate "{gate1_name}" → {len(cameras1)} cameras: {[c.sn for c in cameras1]}')
        self.stdout.write(f'  Create TentGate "{gate2_name}" → {len(cameras2)} cameras: {[c.sn for c in cameras2]}')
        self.stdout.write(f'  Move cameras from "{tent2.name}" to "{merged_name}"')
        self.stdout.write(f'  Delete "{tent2.name}"')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDry run — no changes saved.'))
            return

        with transaction.atomic():
            # Rename tent1 and merge capacity
            tent1.name     = merged_name
            tent1.capacity = tent1.capacity + tent2.capacity
            tent1.save()

            # Create gate records
            gate1 = TentGate.objects.create(tent=tent1, name=gate1_name)
            gate2 = TentGate.objects.create(tent=tent1, name=gate2_name)

            # Assign existing tent1 cameras to gate1
            Camera.objects.filter(id__in=[c.id for c in cameras1]).update(gate=gate1)

            # Move tent2 cameras to tent1, assign to gate2
            Camera.objects.filter(id__in=[c.id for c in cameras2]).update(tent=tent1, gate=gate2)

            # Delete tent2 (all cameras already moved)
            tent2.delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Tent "{merged_name}" now has {len(cameras1)} cameras on "{gate1_name}" '
            f'and {len(cameras2)} cameras on "{gate2_name}".'
        ))
