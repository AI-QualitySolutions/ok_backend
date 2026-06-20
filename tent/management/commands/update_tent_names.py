from django.core.management.base import BaseCommand
from tent.models import Tent
from authentication.models import Company


class Command(BaseCommand):
    help = 'Update the name of each tent with its sequence number within its company.'

    def handle(self, *args, **kwargs):
        # Loop through each company
        for company in Company.objects.all():
            # Get all tents for the company, ordered by creation date or any other order
            tents = Tent.objects.filter(company=company).order_by(
                'created_at')  # Adjust 'created_at' if necessary

            # Loop through the tents and update their names
            for index, tent in enumerate(tents, start=1):
                # Update the name with the sequence
                tent.name = f"{index}"
                tent.save()

            self.stdout.write(self.style.SUCCESS(
                f"Updated {len(tents)} tents for {company.name}"))
