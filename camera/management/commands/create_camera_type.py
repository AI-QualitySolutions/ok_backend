from django.core.management.base import BaseCommand
from camera.models import CameraType

class Command(BaseCommand):
    help = "Generate Camera Types with name and Arabic name"

    def handle(self, *args, **options):
        camera_type_map = {
            "guard": {
                "name": "Guard",
                "name_ar": "الحراسات الامنية"
            },
            "kitchen": {
                "name": "Kitchen",
                "name_ar": "المطابخ الذكية"
            },
            "buffet": {
                "name": "Buffet",
                "name_ar": "البوفية"
            },
            "garbage": {
                "name": "Cleanness",
                "name_ar": "مراقبة النظافة"
            },
            "recycle": {
                "name": "Recycle",
                "name_ar": "مراقبة إعادة التدوير"
            },
            "bathroom": {
                "name": "Cleaner",
                "name_ar": "مراقبة عمال النظافة"
            },
            "sentiment": {
                "name": "Sentiment",
                "name_ar": "قياس رضا العميل"
            },
            "peoplecount": {
                "name": "PeopleCount",
                "name_ar": "حصر أعداد الحجاج"
            }
        }

        try:
            for cam_type, values in camera_type_map.items():
                CameraType.objects.update_or_create(
                    type=cam_type,
                    defaults={
                        "name": values["name"],
                        "name_ar": values["name_ar"]
                    }
                )
            self.stdout.write(self.style.SUCCESS(
                'Successfully generated Camera Types with translations.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Failed to generate Camera Types: {e}'))
