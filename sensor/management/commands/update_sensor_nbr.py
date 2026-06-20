# your_app/management/commands/update_sensor_neighbours.py

from django.core.management.base import BaseCommand
# Replace 'your_app' with your actual app name
from sensor.models import EnvironmentSensor


class Command(BaseCommand):
    help = 'Updates neighbour values for EnvironmentSensor model'

    def handle(self, *args, **kwargs):

        # Sensor data
        sensor_data = {
            "319": {
                "Neighbour_Name_1": "301",
                "Neighbour_Name_2": "328",
                "Neighbour_Name_3": "Master"
            },
            "320": {
                "Neighbour_Name_1": "292",
                "Neighbour_Name_2": "312",
                "Neighbour_Name_3": "Master2"
            }
        }

        # Counter for tracking updates
        updated_count = 0
        errors = []

        for sensor_name, neighbours in sensor_data.items():
            try:
                # Get the sensor instance
                sensor = EnvironmentSensor.objects.filter(name=sensor_name).order_by('-last_entry_time').first()
                if not sensor:
                    errors.append(f"Sensor {sensor_name} not found")
                    continue

                # Update neighbour_name_1
                try:
                    neighbour_1 = EnvironmentSensor.objects.filter(
                        name=neighbours['Neighbour_Name_1']).order_by('-last_entry_time').first()
                    sensor.neighbour_name_1 = neighbour_1
                    sensor.check_neighbour = True
                except EnvironmentSensor.DoesNotExist:
                    sensor.neighbour_name_1 = None
                    errors.append(
                        f"Sensor {sensor_name}: Neighbour_1 {neighbours['Neighbour_Name_1']} not found")

                # Update neighbour_name_2
                try:
                    neighbour_2 = EnvironmentSensor.objects.filter(
                        name=neighbours['Neighbour_Name_2']).order_by('-last_entry_time').first()
                    sensor.neighbour_name_2 = neighbour_2
                    sensor.check_neighbour = True
                except EnvironmentSensor.DoesNotExist:
                    sensor.neighbour_name_2 = None
                    errors.append(
                        f"Sensor {sensor_name}: Neighbour_2 {neighbours['Neighbour_Name_2']} not found")

                # Update neighbour_name_3
                try:
                    neighbour_3 = EnvironmentSensor.objects.filter(
                        name=neighbours['Neighbour_Name_3']).order_by('-last_entry_time').first()
                    sensor.neighbour_name_3 = neighbour_3
                    sensor.check_neighbour = True
                except EnvironmentSensor.DoesNotExist:
                    sensor.neighbour_name_3 = None
                    errors.append(
                        f"Sensor {sensor_name}: Neighbour_3 {neighbours['Neighbour_Name_3']} not found")


                # Save the sensor
                sensor.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully updated sensor {sensor_name}"))

            except EnvironmentSensor.DoesNotExist:
                errors.append(f"Sensor {sensor_name} not found")
                continue

        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f"\nUpdate complete. Successfully updated {updated_count} sensors."))
        if errors:
            self.stdout.write(self.style.WARNING("\nErrors encountered:"))
            for error in errors:
                self.stdout.write(self.style.WARNING(error))
