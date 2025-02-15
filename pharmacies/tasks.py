# pharmacies/tasks.py
from celery import shared_task
from django.utils import timezone

from pharmacies.models import ScraperConfig
from pharmacies.utils import (
    add_scraped_data_to_db,
    get_city_data,
)


@shared_task
def run_scraper(city_name):
    try:
        city_data = get_city_data(city_name=city_name)
        add_scraped_data_to_db(city_data, city_name=city_name)

        scraper = ScraperConfig.objects.get(city__name=city_name)

        scraper.last_run = timezone.now()
        scraper.save()
    except Exception as e:
        print(f"Scraper failed: {str(e)}")
