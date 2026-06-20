import requests
from dateutil import parser as dateutil_parser
from django.core.management.base import BaseCommand

SHELLHUB_URL      = "https://shellhub.aiqualitysolutions.com"
SHELLHUB_USERNAME = "aiqualitysolutions"
SHELLHUB_PASSWORD = "AiQuality@2024#"


class Command(BaseCommand):
    help = "Manually test ShellHub sync and show what would be updated"

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually update last_seen in DB (default: dry-run only)',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        # Step 1: Authenticate
        self.stdout.write("--- Step 1: Authenticating with ShellHub ---")
        try:
            login_resp = requests.post(
                f"{SHELLHUB_URL}/api/login",
                json={"username": SHELLHUB_USERNAME, "password": SHELLHUB_PASSWORD},
                timeout=10,
            )
            self.stdout.write(f"Login status: {login_resp.status_code}")
            self.stdout.write(f"Login response keys: {list(login_resp.json().keys())}")
            login_data = login_resp.json()
        except Exception as e:
            self.stderr.write(f"Login failed: {e}")
            return

        token = login_data.get("token")
        if not token:
            self.stderr.write(f"No 'token' key found. Full response: {login_data}")
            return
        self.stdout.write(f"Token obtained (first 20 chars): {token[:20]}...")

        # Step 2: Fetch all devices
        self.stdout.write("\n--- Step 2: Fetching devices from ShellHub ---")
        try:
            devices_resp = requests.get(
                f"{SHELLHUB_URL}/api/devices",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            self.stdout.write(f"Devices status: {devices_resp.status_code}")
            devices = devices_resp.json()
            if isinstance(devices, list):
                self.stdout.write(f"Total ShellHub devices: {len(devices)}")
            else:
                self.stderr.write(f"Unexpected devices response: {devices}")
                return
        except Exception as e:
            self.stderr.write(f"Devices fetch failed: {e}")
            return

        # Step 3: Print all ShellHub MACs
        self.stdout.write("\n--- Step 3: ShellHub device MACs ---")
        shellhub_macs = {}
        for d in devices:
            mac       = d.get("identity", {}).get("mac", "").strip().lower()
            last_seen = d.get("last_seen", "N/A")
            name      = d.get("name", "N/A")
            self.stdout.write(f"  mac={mac!r:30s}  last_seen={last_seen}  name={name}")
            if mac:
                shellhub_macs[mac] = last_seen

        # Step 4: Compare against DB
        from technical_dashboard.models import OrangePiDevice
        self.stdout.write("\n--- Step 4: DB OrangePiDevice MACs ---")
        db_devices = OrangePiDevice.objects.all()
        for dev in db_devices:
            db_mac = (dev.mac_address or "").strip().lower()
            match = shellhub_macs.get(db_mac)
            self.stdout.write(
                f"  id={dev.id}  mac={db_mac!r:30s}  db_last_seen={dev.last_seen}  "
                f"shellhub_match={'YES → ' + str(match) if match else 'NO MATCH'}"
            )
            if match and apply:
                try:
                    parsed = dateutil_parser.isoparse(match)
                    OrangePiDevice.objects.filter(pk=dev.pk).update(last_seen=parsed)
                    self.stdout.write(self.style.SUCCESS(f"    → Updated last_seen to {parsed}"))
                except Exception as e:
                    self.stderr.write(f"    → Update failed: {e}")

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry-run complete. Add --apply to actually update the DB."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("\nSync applied."))
