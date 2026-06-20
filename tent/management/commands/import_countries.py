import json
from django.core.management.base import BaseCommand
from tent.models import Country

class Command(BaseCommand):
    help = 'Import countries from countries.json file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='countries.json',
            help='Path to the countries.json file'
        )

    def handle(self, *args, **options):
        file_path = options['path']

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                countries_data = json.load(f)

            created_count = 0
            for country in countries_data:
                name = country.get('en')
                name_ar = country.get('ar')

                if name and name_ar:
                    obj, created = Country.objects.get_or_create(name=name, name_ar=name_ar)
                    if created:
                        created_count += 1

            self.stdout.write(self.style.SUCCESS(f'Successfully imported {created_count} countries.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR('Invalid JSON format.'))
