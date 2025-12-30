"""
Celery tasks for the Pharmacies application.

This module defines background tasks for scraping pharmacy data from various sources
and updating the database.
"""

from celery import shared_task
from django.utils import timezone

from pharmacies.models import ScraperConfig
from pharmacies.utils import (
    add_scraped_data_to_db,
    get_city_data,
)


@shared_task
def run_scraper(city_name: str) -> None:
    """
    Execute the scraper for a specific city and save results to the database.

    This Celery task:
    1. Fetches data for the given city using the appropriate scraper strategy.
    2. Saves the scraped pharmacy data to the database.
    3. Updates the ScraperConfig's last_run timestamp.
    """
    print(f"Running scraper for city {city_name}")
    city_data = get_city_data(city_name=city_name)
    print(f"Scraper for city {city_name} finished")
    add_scraped_data_to_db(city_data, city_name=city_name)
    print(f"Scraper data for city {city_name} saved to DB")

    rows_updated = ScraperConfig.objects.filter(city__name=city_name).update(
        last_run=timezone.now()
    )
    if rows_updated:
        print(f"Scraper config for city {city_name} updated")
    else:
        print(f"No ScraperConfig found for city {city_name}")
