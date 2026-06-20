from django.core.management.base import BaseCommand
from tent.models import Tent, Company
from django.db import transaction

class Command(BaseCommand):
    help = "Rename Tent names sequentially per company"

    def handle(self, *args, **options):
        with transaction.atomic():
            companies = Company.objects.all()
            for company in companies:
                tents = Tent.objects.filter(company=company).order_by('id')
                for index, tent in enumerate(tents, start=1):
                    new_name = f"{index}"
                    if tent.name != new_name:
                        self.stdout.write(f"{company.name}: Renaming {tent.name} -> {new_name}")
                        tent.name = new_name
                        tent.save()
        self.stdout.write(self.style.SUCCESS("Tent names updated company-wise."))
