from datetime import datetime
from unittest.mock import MagicMock, patch

from pharmacies.utils.eskisehireo_scraper import (
    _get_district_from_name,
    _get_duty_dates,
    get_eskisehir_data,
)


def test_get_district_from_name() -> None:
    assert _get_district_from_name("TEST ECZANESİ ODUNPAZARI") == "ODUNPAZARI"


def test_get_duty_dates() -> None:
    operation_times = "16.12.2025 09:00 - 17.12.2025 09:00"
    start, end = _get_duty_dates(operation_times)
    assert start == datetime(2025, 12, 16, 9, 0)
    assert end == datetime(2025, 12, 17, 9, 0)


@patch("pharmacies.utils.eskisehireo_scraper.requests.get")
@patch("pharmacies.utils.utils.get_coordinates_from_google_maps_url")
def test_get_eskisehir_data(mock_get_coords: MagicMock, mock_get: MagicMock) -> None:
    mock_get_coords.return_value = {"lat": 39.7, "lng": 30.5}

    html_content = """
    <div class="nobetci">
        <h4 class="text-danger">TEST ECZANESİ - ODUNPAZARI</h4>
        <i class="fa fa-home"></i> Test Address
        <a href="tel:123456">123456</a>
        <a href="https://www.google.com/maps/dir/?api=1&destination=39.7,30.5">Map</a>
        <span class="text-danger">16.12.2025 09:00 - 17.12.2025 09:00</span>
    </div>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_get.return_value = mock_response

    data = get_eskisehir_data()

    assert len(data) == 1
    assert data[0]["name"] == "TEST ECZANESİ"
    assert data[0]["address"] == "Test Address"
    assert data[0]["district"] == "ODUNPAZARI"
    assert data[0]["phone"] == "123456"
    assert data[0]["coordinates"] == {"lat": 39.7, "lng": 30.5}
    assert data[0]["duty_start"] == datetime(2025, 12, 16, 9, 0)
    assert data[0]["duty_end"] == datetime(2025, 12, 17, 9, 0)


@patch("pharmacies.utils.eskisehireo_scraper.requests.get")
def test_get_eskisehir_data_no_h4(mock_get: MagicMock) -> None:
    html_content = """
    <div class="nobetci">
        <!-- No h4 tag here -->
    </div>
    """
    mock_response = MagicMock()
    mock_response.text = html_content
    mock_get.return_value = mock_response

    data = get_eskisehir_data()
    assert len(data) == 0
