import random
from django.core.management.base import BaseCommand
from authentication.models import MyUser, Company
from tent.models import Tent

class Command(BaseCommand):
    help = "Create an admin and staff users for each company"

    def handle(self, *args, **kwargs):
        male_names = ["Abdullah", "Mohammed", "Fahad", "Sultan",
                      "Khalid", "Nasser", "Saud", "Omar", "Majed", "Salman"]
        female_names = ["Aisha", "Fatimah", "Noor", "Reem",
                        "Layla", "Hanan", "Nada", "Sara", "Amal", "Maha"]
        surnames = ["Al-Saud", "Al-Rashid", "Al-Harbi", "Al-Qahtani", "Al-Dosari",
                    "Al-Zahrani", "Al-Otaibi", "Al-Mutairi", "Al-Shamrani", "Al-Subaie"]

        companies = Company.objects.all()

        for company in companies:
            tents = Tent.objects.filter(company=company)
            if not tents.exists():
                self.stdout.write(self.style.WARNING(f"No tents for company: {company.name}. Skipping."))
                continue

            # Create Admin
            first, last = random.choice(male_names), random.choice(surnames)
            email = f"{first.lower()}.{last.lower()}_admin_{company.id}@example.com"
            username = f"{first.lower()}admin{company.id}"

            if not MyUser.objects.filter(email=email).exists():
                user = MyUser(
                    email=email,
                    username=username,
                    company=company,
                    is_admin=True,
                    is_staff=True,
                    sensor_update_permission=True
                )
                user.set_password("123456")
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created admin user for {company.name}: {email}"))

            # Create 3 Staff Users
            for i in range(3):
                first = random.choice(female_names + male_names)
                last = random.choice(surnames)
                email = f"{first.lower()}.{last.lower()}_staff{i}_{company.id}@example.com"
                username = f"{first.lower()}staff{i}{company.id}"

                if MyUser.objects.filter(email=email).exists():
                    self.stdout.write(self.style.WARNING(f"User {email} already exists. Skipping."))
                    continue

                user = MyUser(
                    email=email,
                    username=username,
                    company=company,
                    is_admin=False,
                    is_staff=True,
                    sensor_update_permission=random.choice([True, False])
                )
                user.set_password("123456")
                user.save()

                assigned = random.sample(list(tents), min(3, tents.count()))
                user.assigned_tent.set(assigned)

                self.stdout.write(self.style.SUCCESS(f"Created staff user for {company.name}: {email}"))
