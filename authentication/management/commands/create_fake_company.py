import random
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from faker import Faker
from PIL import Image
# Replace with your actual app and model import
from authentication.models import Company

fake = Faker()


class Command(BaseCommand):
    help = 'Create 10 fake companies'

    def handle(self, *args, **kwargs):
        for _ in range(10):
            name = fake.unique.company()

            # Generate a simple dummy image in memory
            image = Image.new('RGB', (100, 100), color=(random.randint(
                0, 255), random.randint(0, 255), random.randint(0, 255)))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            image_file = ContentFile(buffer.getvalue())

            company = Company(
                name=name,
                is_temperature=random.choice([True, False]),
                is_guard=random.choice([True, False]),
                is_headcount=random.choice([True, False]),
                is_kitchen=random.choice([True, False]),
                is_foodweight=random.choice([True, False]),
                is_cleanness=random.choice([True, False]),
                is_buffet=random.choice([True, False]),
                is_water_tank=random.choice([True, False]),
                is_environment_sensor=random.choice([True, False]),
            )
            company.logo.save(
                f"{name.replace(' ', '_')}.png", image_file, save=True)

            self.stdout.write(self.style.SUCCESS(f'Created company: {name}'))
