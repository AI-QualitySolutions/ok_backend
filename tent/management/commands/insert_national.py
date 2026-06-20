import json
from django.core.management.base import BaseCommand
from tent.models import Tent
from authentication.models import Company  # Replace 'yourapp' with your app name
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Import tents from NCC.json'

    def handle(self, *args, **kwargs):
        json_path = 'NCC.json'  # You can customize the path

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                tents_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ File {json_path} not found.'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'❌ JSON decode error: {e}'))
            return

        created_count = 0
        company_name = "National Catering Company"

        # Get or create the company
        company, _ = Company.objects.get_or_create(name=company_name)

        for item in tents_data:
            name = item.get('name')
            is_arafa = item.get('is_arafa', False)

            if not name:
                self.stdout.write(self.style.WARNING('⚠️ Skipped entry with missing name'))
                continue

            tent = Tent.objects.create(
                name=name,
                company=company,
                is_arafa=is_arafa,
                longitude="0.000000",  # Placeholder
                latitude="0.000000"    # Placeholder
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'✅ Tent created: {name}'))

        self.stdout.write(self.style.SUCCESS(f'🎉 {created_count} tents successfully imported from {json_path}.'))
