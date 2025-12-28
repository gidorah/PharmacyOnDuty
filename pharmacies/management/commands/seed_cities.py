from datetime import time
from typing import Any

from django.core.management.base import BaseCommand

from pharmacies.models import City, ScraperConfig, WorkingSchedule


class Command(BaseCommand):
    help = "Seeds cities, working schedules and scraper configs"

    def handle(self, *args: Any, **kwargs: Any) -> None:
        cities = ["eskisehir", "istanbul", "ankara"]

        # Define working hours in UTC (+3 for istanbul)
        # 08:30 TRT -> 05:30 UTC
        # 18:30 TRT -> 15:30 UTC
        weekday_start = time(5, 30)
        weekday_end = time(15, 30)

        # Saturday hours (example)
        # 10:00 TRT -> 07:00 UTC
        # 18:00 TRT -> 15:00 UTC
        saturday_start = time(7, 0)
        saturday_end = time(15, 0)

        for city_name in cities:
            # 1. Create or get the city
            city, created = City.objects.get_or_create(name=city_name)
            action = "Created" if created else "Existing"
            self.stdout.write(f"City '{city.name}': {action}")

            # 2. Create or update the WorkingSchedule
            schedule, created = WorkingSchedule.objects.update_or_create(
                city=city,
                defaults={
                    "weekday_start": weekday_start,
                    "weekday_end": weekday_end,
                    "saturday_start": saturday_start,
                    "saturday_end": saturday_end,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  - WorkingSchedule: {action}")

            # 3. Create or update ScraperConfig
            # Run every 1 hour
            scraper_config, created = ScraperConfig.objects.update_or_create(
                city=city, defaults={"interval": 1}
            )

            # calling save() triggers _update_celery_schedule (update_or_create calls save)
            # but we can call it again just to be safe if logic depends on other fields
            scraper_config.save()

            action = "Created" if created else "Updated"
            self.stdout.write(
                f"  - ScraperConfig: {action} (Interval: {scraper_config.interval}h)"
            )
