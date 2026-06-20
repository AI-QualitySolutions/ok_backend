# File: yourapp/management/commands/create_tents_and_sensors.py

from django.core.management.base import BaseCommand
from weight.models import Tent, EnvironmentSensor


class Command(BaseCommand):
    help = 'Create one weight sensor for each specified tent, using tent.name as sn and name.'

    def handle(self, *args, **kwargs):
        tent_ids = [7, 8, 26, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 43, 44, 45, 50, 71]

        for tent_id in tent_ids:
            try:
                tent = Tent.objects.get(name=tent_id, company__name__icontains="albait", is_arafa=False)
            except Tent.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"❌ Tent with ID {tent_id} not found or doesn't match criteria."))
                continue

            # Check if a sensor already exists for this tent with the same name
            if EnvironmentSensor.objects.filter(tent=tent, sn=tent.name).exists():
                self.stdout.write(self.style.WARNING(f"⚠️ Sensor for tent '{tent.name}' already exists. Skipping."))
                continue

            EnvironmentSensor.objects.create(
                tent=tent,
                sn=tent.name,
                name=tent.name,
                type="weight"
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Created sensor for tent '{tent.name}'"))

        self.stdout.write(self.style.SUCCESS("🎉 Sensor creation process completed."))
