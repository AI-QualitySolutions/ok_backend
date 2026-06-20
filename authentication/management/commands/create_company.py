from django.core.management.base import BaseCommand
from authentication.models import Company

class Command(BaseCommand):
    help = 'Interactively creates a new company'

    def handle(self, *args, **options):
        # Prompt for company name
        name = input("Enter company name: ").strip()

        if not name:
            self.stderr.write(self.style.ERROR("Company name is required."))
            return

        if Company.objects.filter(name=name).exists():
            self.stdout.write(self.style.WARNING(f"Company '{name}' already exists."))
            return

        company = Company.objects.create_company(name=name)
        self.stdout.write(self.style.SUCCESS(f"Company '{company.name}' created successfully."))
