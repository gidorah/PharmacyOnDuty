from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from pharmacies.utils.ankaraeo_scraper import _get_duty_times, get_ankara_data


@patch("pharmacies.utils.ankaraeo_scraper.timezone.now")
def test_get_duty_times_weekday_afternoon(mock_now: MagicMock) -> None:
    # Tuesday, Dec 16, 2025, 14:00

    mock_now.return_value = datetime(2025, 12, 16, 14, 0, tzinfo=UTC)

    duty_start, duty_end = _get_duty_times()

    assert duty_start == datetime(2025, 12, 16, 16, 0, tzinfo=UTC)

    assert duty_end == datetime(2025, 12, 17, 6, 0, tzinfo=UTC)


@patch("pharmacies.utils.ankaraeo_scraper.timezone.now")
def test_get_duty_times_weekday_morning(mock_now: MagicMock) -> None:
    # Tuesday, Dec 16, 2025, 05:00

    mock_now.return_value = datetime(2025, 12, 16, 5, 0, tzinfo=UTC)

    duty_start, duty_end = _get_duty_times()

    # Should be for Monday's duty

    assert duty_start == datetime(2025, 12, 15, 16, 0, tzinfo=UTC)

    assert duty_end == datetime(2025, 12, 16, 6, 0, tzinfo=UTC)


@patch("pharmacies.utils.ankaraeo_scraper.timezone.now")
def test_get_duty_times_sunday(mock_now: MagicMock) -> None:
    # Sunday, Dec 21, 2025, 10:00

    mock_now.return_value = datetime(2025, 12, 21, 10, 0, tzinfo=UTC)

    duty_start, duty_end = _get_duty_times()

    assert duty_start == datetime(2025, 12, 21, 6, 0, tzinfo=UTC)

    assert duty_end == datetime(2025, 12, 22, 6, 0, tzinfo=UTC)


@patch("pharmacies.utils.ankaraeo_scraper.requests.get")
@patch("pharmacies.utils.ankaraeo_scraper._get_duty_times")
def test_get_ankara_data(mock_duty_times: MagicMock, mock_get: MagicMock) -> None:
    mock_duty_times.return_value = (
        datetime(2025, 12, 16, 16, 0, tzinfo=UTC),
        datetime(2025, 12, 17, 6, 0, tzinfo=UTC),
    )

    mock_response = MagicMock()

    mock_response.json.return_value = {
        "NobetciEczaneBilgisiListesi": [
            {
                "EczaneAdi": "TEST",
                "EczaneAdresi": "Address 1",
                "IlceAdi": "Çankaya",
                "Telefon": "123456",
                "KoordinatLat": "39.9",
                "KoordinatLng": "32.8",
            }
        ]
    }

    mock_get.return_value = mock_response

    data = get_ankara_data()

    assert len(data) == 1

    assert data[0]["name"] == "Test Eczanesi"

    assert data[0]["address"] == "Address 1"

    assert data[0]["district"] == "Çankaya"

    assert data[0]["phone"] == "123456"

    assert data[0]["coordinates"] == {"lat": 39.9, "lng": 32.8}

    assert data[0]["duty_start"] == datetime(2025, 12, 16, 16, 0, tzinfo=UTC)

    assert data[0]["duty_end"] == datetime(2025, 12, 17, 6, 0, tzinfo=UTC)
