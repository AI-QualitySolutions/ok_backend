"""
Management command to add gates to an existing tent and assign cameras to them.

Usage examples:

  # List all tents with their IDs
  python manage.py manage_tent_gates --list-tents

  # Show current cameras and gate assignments for a tent
  python manage.py manage_tent_gates --tent-id 42 --show

  # Add a new gate to a tent
  python manage.py manage_tent_gates --tent-id 42 --add-gate "Gate 2"

  # Assign cameras to a gate (by camera SN, comma-separated)
  python manage.py manage_tent_gates --tent-id 42 --gate-id 5 --assign-cameras "SN001,SN002,SN003"

  # Unassign cameras from their gate (set gate to None)
  python manage.py manage_tent_gates --tent-id 42 --unassign-cameras "SN001"
"""
from django.core.management.base import BaseCommand, CommandError
from tent.models import Tent, TentGate
from camera.models import Camera


class Command(BaseCommand):
    help = 'Add gates to a tent and assign cameras to them.'

    def add_arguments(self, parser):
        parser.add_argument('--tent-id', type=int, dest='tent_id', help='Tent ID to manage')
        parser.add_argument('--list-tents', action='store_true', dest='list_tents', help='List all tents with IDs')
        parser.add_argument('--show', action='store_true', dest='show', help='Show cameras and gate assignments for the tent')
        parser.add_argument('--add-gate', type=str, dest='add_gate', help='Create a new gate with this name')
        parser.add_argument('--gate-id', type=int, dest='gate_id', help='Gate ID to assign cameras to')
        parser.add_argument('--assign-cameras', type=str, dest='assign_cameras', help='Comma-separated camera SNs to assign to --gate-id')
        parser.add_argument('--unassign-cameras', type=str, dest='unassign_cameras', help='Comma-separated camera SNs to remove from their gate')

    def handle(self, *args, **options):
        if options['list_tents']:
            self.stdout.write('\nAll tents (id | company | name | gates):')
            for t in Tent.objects.select_related('company').prefetch_related('gates').order_by('company__name', 'name'):
                company = t.company.name if t.company else '—'
                gates = ', '.join(g.name for g in t.gates.all()) or 'no gates'
                self.stdout.write(f'  {t.id:>5}  {company:<30}  {t.name:<30}  [{gates}]')
            return

        if not options['tent_id']:
            raise CommandError('--tent-id is required. Use --list-tents to find IDs.')

        try:
            tent = Tent.objects.select_related('company').get(pk=options['tent_id'])
        except Tent.DoesNotExist:
            raise CommandError(f'Tent with id={options["tent_id"]} not found.')

        if options['show']:
            self._show_tent(tent)
            return

        if options['add_gate']:
            gate = TentGate.objects.create(tent=tent, name=options['add_gate'])
            self.stdout.write(self.style.SUCCESS(
                f'Created gate "{gate.name}" (id={gate.id}) for tent "{tent.name}".'
            ))
            self._show_tent(tent)
            return

        if options['assign_cameras']:
            if not options['gate_id']:
                raise CommandError('--gate-id is required when using --assign-cameras.')
            try:
                gate = TentGate.objects.get(pk=options['gate_id'], tent=tent)
            except TentGate.DoesNotExist:
                raise CommandError(f'Gate id={options["gate_id"]} not found for tent "{tent.name}".')

            sns = [s.strip() for s in options['assign_cameras'].split(',') if s.strip()]
            updated = Camera.objects.filter(tent=tent, sn__in=sns).update(gate=gate)
            not_found = set(sns) - set(Camera.objects.filter(tent=tent, sn__in=sns).values_list('sn', flat=True))
            self.stdout.write(self.style.SUCCESS(f'Assigned {updated} camera(s) to gate "{gate.name}".'))
            if not_found:
                self.stdout.write(self.style.WARNING(f'Not found in this tent: {not_found}'))
            self._show_tent(tent)
            return

        if options['unassign_cameras']:
            sns = [s.strip() for s in options['unassign_cameras'].split(',') if s.strip()]
            updated = Camera.objects.filter(tent=tent, sn__in=sns).update(gate=None)
            self.stdout.write(self.style.SUCCESS(f'Removed gate assignment from {updated} camera(s).'))
            self._show_tent(tent)
            return

        # Default: just show the tent
        self._show_tent(tent)

    def _show_tent(self, tent):
        cameras = Camera.objects.filter(tent=tent, type='peoplecount').select_related('gate').order_by('gate__name', 'sn')
        gates = list(TentGate.objects.filter(tent=tent).order_by('name'))

        self.stdout.write(f'\nTent: "{tent.name}" (id={tent.id})')
        self.stdout.write(f'Gates:')
        if gates:
            for g in gates:
                self.stdout.write(f'  [{g.id}] {g.name}')
        else:
            self.stdout.write('  (none)')

        self.stdout.write(f'Peoplecount cameras:')
        if cameras:
            for c in cameras:
                gate_label = f'{c.gate.name} (id={c.gate.id})' if c.gate else 'no gate'
                self.stdout.write(f'  sn={c.sn}  gate={gate_label}')
        else:
            self.stdout.write('  (none)')
