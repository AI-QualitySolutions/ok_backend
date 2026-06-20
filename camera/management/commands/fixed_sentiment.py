import json
from django.core.management.base import BaseCommand
from camera.models import SentimentAnalysis


class Command(BaseCommand):
    help = "Fix sentiment_list fields stored as strings instead of list of strings."

    def handle(self, *args, **kwargs):
        status_fixed = 0
        count = 0
        items = SentimentAnalysis.objects.all()

        for item in items:
            if isinstance(item.sentiment_list, str):
                try:
                    # Try parsing the string into a list
                    parsed_list = json.loads(item.sentiment_list)

                    # Ensure it's a list of strings
                    if isinstance(parsed_list, list) and all(isinstance(s, str) for s in parsed_list):
                        item.sentiment_list = parsed_list
                        item.save()
                        count += 1
                except json.JSONDecodeError:
                    self.stdout.write(self.style.WARNING(
                        f"Failed to parse: {item.sentiment_list}"))
            else:
                if item.current_status and (
                    not item.annotator_status or any(
                        s is None for s in item.annotator_status)
                ):
                    status = [
                        s for s in item.current_status if s is not None]
                    item.annotator_status = status
                    status_fixed += 1
                item.save()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully fixed {count} sentiment_list entries."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Successfully fixed {status_fixed} annotator_status entries."
        ))
