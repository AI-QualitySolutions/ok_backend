from django.utils import timezone
from django.core.management.base import BaseCommand
from weight.models import WeightConditions

class Command(BaseCommand):
    help = 'Create fake tents and weight sensors'

    def handle(self, *args, **kwargs):
        try:
            # Deleting existing WeightConditions entries
            WeightConditions.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing WeightConditions deleted."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to delete existing WeightConditions: {e}"))

        try:
            # Create a new WeightConditions entry with timezone-aware datetimes
            WeightConditions.objects.create(
                breakfast_start="06:00:00",
                breakfast_end="09:00:00",
                lunch_start="12:00:00",
                lunch_end="14:00:00",
                dinner_start="17:00:00",
                dinner_end="23:59:00",
                breakfast_weight_accepted=300,  # Example weight accepted for breakfast
                lunch_weight_accepted=400,  # Example weight accepted for lunch
                dinner_weight_accepted=400,  # Example weight accepted for dinner
                start_date=timezone.now(),  # Timezone-aware current date and time
                end_date=timezone.now()  # Timezone-aware current date and time
            )
            self.stdout.write(self.style.SUCCESS("WeightConditions created."))
        except Exception as e: 
            self.stdout.write(self.style.ERROR(f"Failed to create WeightConditions: {e}"))
