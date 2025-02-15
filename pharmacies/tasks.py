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
def run_scraper(scraper_id):
    scraper = ScraperConfig.objects.get(id=scraper_id)

    try:
        if scraper.city.name == "ankara":
            ankaraeo_scraper.main()
        elif scraper.city.name == "eskisehir":
            eskisehireo_scraper.main()
        elif scraper.city.name == "istanbul":
            istanbul_saglik_scraper.main()

        scraper.last_run = timezone.now()
        scraper.save()
    except Exception as e:
        print(f"Scraper failed: {str(e)}")
