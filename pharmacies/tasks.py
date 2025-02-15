# pharmacies/tasks.py
from celery import shared_task
from django.utils import timezone

from pharmacies.models import ScraperConfig
from pharmacies.utils import (
    ankaraeo_scraper,
    eskisehireo_scraper,
    istanbul_saglik_scraper,
)


@shared_task
def run_scraper(city_name):
    try:
        if city_name == "ankara":
            ankaraeo_scraper.main()
        elif city_name == "eskisehir":
            eskisehireo_scraper.main()
        elif city_name == "istanbul":
            istanbul_saglik_scraper.main()

        scraper = ScraperConfig.objects.get(city__name=city_name)

        scraper.last_run = timezone.now()
        scraper.save()
    except Exception as e:
        print(f"Scraper failed: {str(e)}")
