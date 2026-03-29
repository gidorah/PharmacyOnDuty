from contextlib import nullcontext
from json import JSONDecodeError
from unittest.mock import MagicMock, patch

from django.db.utils import InterfaceError
from requests.exceptions import RequestException

from pharmacies.tasks import run_scraper


@patch("pharmacies.tasks.logger")
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_skips_persistence_on_upstream_json_error(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_get_city_data.side_effect = JSONDecodeError("Expecting value", "", 0)

    run_scraper("ankara")

    mock_persist.assert_not_called()
    mock_logger.warning.assert_called_once()
    assert mock_close_old_connections.call_count == 2


@patch("pharmacies.tasks.logger")
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_skips_persistence_on_upstream_request_error(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_get_city_data.side_effect = RequestException("down")

    run_scraper("istanbul")

    mock_persist.assert_not_called()
    mock_logger.warning.assert_called_once()
    assert mock_close_old_connections.call_count == 2


@patch("pharmacies.tasks.logger")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.utils.istanbul_saglik_scraper.requests.post")
@patch("pharmacies.utils.istanbul_saglik_scraper.DISTRICTS", ["Adalar"])
def test_run_scraper_handles_istanbul_request_failures_through_dispatcher(
    mock_post: MagicMock,
    mock_persist: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_post.side_effect = RequestException("down")

    run_scraper("istanbul")

    mock_persist.assert_not_called()
    mock_logger.warning.assert_called_once()


@patch("pharmacies.tasks.logger")
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_skips_empty_scrapes(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_get_city_data.return_value = []

    run_scraper("istanbul")

    mock_persist.assert_not_called()
    mock_logger.warning.assert_called_once()
    assert mock_close_old_connections.call_count == 2


@patch("pharmacies.tasks.logger")
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_retries_after_stale_db_connection(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_get_city_data.return_value = [{"name": "Example"}]
    mock_persist.side_effect = [InterfaceError("connection already closed"), 1]

    run_scraper("istanbul")

    assert mock_persist.call_count == 2
    mock_logger.warning.assert_called_once()
    assert mock_close_old_connections.call_count == 4


@patch("pharmacies.tasks.transaction.atomic")
@patch("pharmacies.tasks.ScraperConfig.objects.filter")
@patch("pharmacies.tasks.add_scraped_data_to_db")
@patch("pharmacies.tasks.logger")
def test_run_scraper_retries_real_persistence_helper_path(
    mock_logger: MagicMock,
    mock_add_scraped_data_to_db: MagicMock,
    mock_filter: MagicMock,
    mock_atomic: MagicMock,
) -> None:
    mock_atomic.return_value = nullcontext()
    mock_filter.return_value.update.return_value = 1
    scraped_data = [
        {
            "name": "Example Pharmacy",
            "address": "Example Address",
            "district": "Kadikoy",
            "phone": "123456",
            "coordinates": {"lat": 41.0, "lng": 28.9},
            "duty_start": MagicMock(),
            "duty_end": MagicMock(),
        }
    ]
    mock_add_scraped_data_to_db.side_effect = [
        InterfaceError("connection already closed"),
        None,
    ]

    with patch("pharmacies.tasks.get_city_data", return_value=scraped_data):
        run_scraper("istanbul")

    assert mock_add_scraped_data_to_db.call_count == 2
    mock_filter.assert_called_once_with(city__name="istanbul")
    mock_filter.return_value.update.assert_called_once()
    mock_logger.warning.assert_called_once()
