from datetime import time
from django.core.management.base import BaseCommand
from pharmacies.models import City, WorkingSchedule


class Command(BaseCommand):
    help = "Creates a WorkingSchedule for the city of Eskişehir"

    def handle(self, *args, **kwargs):
        # Create or get the city
        city, created = City.objects.get_or_create(name="eskisehir")
        if created:
            self.stdout.write(f"City '{city.name}' created.")
        else:
            self.stdout.write(f"City '{city.name}' already exists.")

        # Define working hours in UTC (+3 for istanbul)
        weekday_start = time(5, 30)
        weekday_end = time(15, 30)
        saturday_start = time(7, 0)
        saturday_end = time(15, 0)

        # Create or update the WorkingSchedule
        schedule, created = WorkingSchedule.objects.update_or_create(
            city=city,
            defaults={
                "weekday_start": weekday_start,
                "weekday_end": weekday_end,
                "saturday_start": saturday_start,
                "saturday_end": saturday_end,
            },
        )

        if created:
            self.stdout.write(f"WorkingSchedule created for city '{city.name}'.")
        else:
            self.stdout.write(f"WorkingSchedule updated for city '{city.name}'.")
