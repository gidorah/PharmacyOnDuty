from contextlib import nullcontext
from json import JSONDecodeError
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest
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
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.utils.istanbul_edevlet_scraper.requests.Session")
def test_run_scraper_handles_istanbul_request_failures_through_dispatcher(
    mock_session_class: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    mock_logger: MagicMock,
) -> None:
    mock_session_class.return_value.get.side_effect = RequestException("down")

    run_scraper("istanbul")

    mock_session_class.return_value.get.assert_called_once()
    mock_persist.assert_not_called()
    mock_logger.warning.assert_called_once_with(
        "Skipping scraper for city %s due to upstream fetch failure.",
        "istanbul",
        exc_info=True,
    )


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
@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks.logger")
def test_run_scraper_retries_real_persistence_helper_path(
    mock_logger: MagicMock,
    mock_close_old_connections: MagicMock,
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


@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_logs_progress_instead_of_printing(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_get_city_data.return_value = [{"name": "Example"}]
    mock_persist.return_value = 1

    with TestCase().assertLogs("pharmacies.tasks", "INFO") as logs:
        run_scraper("ankara")

    assert [record.getMessage() for record in logs.records] == [
        "Running scraper for city ankara",
        "Scraper for city ankara finished",
        "Scraper data for city ankara saved to DB",
        "Scraper config for city ankara updated",
    ]
    for record in logs.records:
        assert record.levelname == "INFO"
        assert record.args == ("ankara",)
        assert "%s" in str(record.msg)
    assert capsys.readouterr().out == ""


@patch("pharmacies.tasks.close_old_connections")
@patch("pharmacies.tasks._persist_scraped_data")
@patch("pharmacies.tasks.get_city_data")
def test_run_scraper_logs_missing_scraper_config(
    mock_get_city_data: MagicMock,
    mock_persist: MagicMock,
    mock_close_old_connections: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_get_city_data.return_value = [{"name": "Example"}]
    mock_persist.return_value = 0

    with TestCase().assertLogs("pharmacies.tasks", "INFO") as logs:
        run_scraper("eskisehir")

    last = logs.records[-1]
    assert last.getMessage() == "No ScraperConfig found for city eskisehir"
    assert last.levelname == "INFO"
    assert last.args == ("eskisehir",)
    assert capsys.readouterr().out == ""
