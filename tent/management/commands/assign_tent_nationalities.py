from django.core.management.base import BaseCommand
from tent.models import Tent, Country

class Command(BaseCommand):
    help = "Assign countries to tents based on tent names or IDs"

    def handle(self, *args, **kwargs):
        country_tent_map = {
            "VIP": [1, 2],
            "Sri Lanka": [3],
            "Bohra": [5],
            "Pakistan": [7],
            "Bangladesh": [7, 8],
            "India": [9],
            "Yemen": [20, 21, 22, 23, 24, 25],
            "Comoros": [26],
            "Afghanistan": [30, 31, 32, 33, 34, 35, 36, 37, 38],
            "Iraq": [40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50],
            "Indonesia": [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 444, 222],
            "Ghana": ["71-1", "71-2"],
            "Bahrain": ["99-1", "99-2"],
            "Brunei": [222],
        }

        updated_count = 0

        for country_name, tent_ids in country_tent_map.items():
            try:
                country = Country.objects.get(name__iexact=country_name)
            except Country.DoesNotExist:
                country = Country.objects.create(name=country_name)

            tents = Tent.objects.filter(name__in=tent_ids, company__name__icontains='albait')

            for tent in tents:
                tent.nationality.add(country)  # use set() if you want to replace all instead
                tent.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✔ Assigned country '{country.name}' to tent '{tent.name}' (ID: {tent.id})")
                )

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Done. Total tents updated: {updated_count}"))
