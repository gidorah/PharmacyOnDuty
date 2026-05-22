"""
Celery tasks for the Pharmacies application.

This module defines background tasks for scraping pharmacy data from various sources
and updating the database.
"""

import logging
from json import JSONDecodeError
from typing import Any

from celery import shared_task
from django.db import close_old_connections, transaction
from django.db.utils import InterfaceError
from django.utils import timezone
from requests.exceptions import RequestException

from pharmacies.models import ScraperConfig
from pharmacies.utils import (
    add_scraped_data_to_db,
    get_city_data,
)

logger = logging.getLogger(__name__)


def _persist_scraped_data(city_data: list[dict[str, Any]], city_name: str) -> int:
    with transaction.atomic():
        add_scraped_data_to_db(city_data, city_name=city_name)
        return ScraperConfig.objects.filter(city__name=city_name).update(
            last_run=timezone.now()
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
    try:
        close_old_connections()
        logger.info("Running scraper for city %s", city_name)
        city_data = get_city_data(city_name=city_name)
        logger.info("Scraper for city %s finished", city_name)
        if not city_data:
            logger.warning(
                "Scraper for city %s returned no data; skipping persistence update.",
                city_name,
            )
            return

        close_old_connections()
        try:
            rows_updated = _persist_scraped_data(city_data, city_name)
        except InterfaceError:
            logger.warning(
                "Retrying scraper persistence for city %s after a stale database connection.",
                city_name,
                exc_info=True,
            )
            close_old_connections()
            rows_updated = _persist_scraped_data(city_data, city_name)

        logger.info("Scraper data for city %s saved to DB", city_name)
        if rows_updated:
            logger.info("Scraper config for city %s updated", city_name)
        else:
            logger.warning("No ScraperConfig found for city %s", city_name)
    except (JSONDecodeError, RequestException):
        logger.warning(
            "Skipping scraper for city %s due to upstream fetch failure.",
            city_name,
            exc_info=True,
        )
        return
    finally:
        close_old_connections()
