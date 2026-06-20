from django.core.management.base import BaseCommand
from camera.models import KitchenImage, Tent, Camera
from django.core.files.base import ContentFile
from faker import Faker
from PIL import Image
import random
import io

fake = Faker()


class Command(BaseCommand):
    help = 'Generate 1,000,000 fake KitchenImage records'

    def add_arguments(self, parser):
        parser.add_argument('--total', type=int, default=1000000)
        parser.add_argument('--batch', type=int, default=1000)
        parser.add_argument('--with-image', action='store_true',
                            help="Generate actual images")

    def handle(self, *args, **options):
        total = options['total']
        batch_size = options['batch']
        with_image = options['with_image']

        tents = list(Tent.objects.all())
        cameras = list(Camera.objects.all())

        if not tents or not cameras:
            self.stdout.write(self.style.WARNING('No Tent or Camera found.'))
            return

        total_batches = total // batch_size

        for batch_num in range(total_batches):
            kitchen_images = []

            for _ in range(batch_size):
                kitchen_image = KitchenImage(
                    tent=random.choice(tents),
                    camera=random.choice(cameras),
                    location=fake.address()
                )

                if with_image:
                    image = self.generate_image()
                    kitchen_image.image.save(fake.file_name(
                        extension='jpg'), image, save=False)
                else:
                    # Use a dummy path (must exist in media root, or use default image)
                    kitchen_image.image.name = 'kitchen_images/dummy.jpg'

                kitchen_images.append(kitchen_image)

            # Save in bulk without hitting DB individually
            KitchenImage.objects.bulk_create(
                kitchen_images, batch_size=batch_size)

            self.stdout.write(
                f'Batch {batch_num + 1}/{total_batches} inserted.')

        self.stdout.write(self.style.SUCCESS(
            f'{total} KitchenImage records created.'))

    def generate_image(self):
        img = Image.new('RGB', (640, 640), color=(random.randint(
            0, 255), random.randint(0, 255), random.randint(0, 255)))
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=70)
        output.seek(0)
        return ContentFile(output.read())
