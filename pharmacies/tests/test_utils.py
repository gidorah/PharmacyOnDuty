from datetime import UTC, datetime, time, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point

from pharmacies.models import City, Pharmacy, WorkingSchedule
from pharmacies.utils.utils import (
    extract_city_name_from_google_maps_response,
    get_city_name_from_location,
    get_coordinates_from_google_maps_url,
    get_map_points_from_fetched_data,
    get_map_points_from_pharmacies,
    order_data_by_distance,
    round_lat_lng,
)


def test_get_coordinates_from_google_maps_url() -> None:
    url = "https://www.google.com/maps/dir/?api=1&destination=39.7,30.5"
    coords = get_coordinates_from_google_maps_url(url)
    assert coords == {"lat": 39.7, "lng": 30.5}


def test_get_map_points_from_fetched_data() -> None:
    data = [
        {
            "geometry": {"location": {"lat": 39.7, "lng": 30.5}},
            "name": "Test Pharmacy",
            "vicinity": "Test Address",
        }
    ]
    points = get_map_points_from_fetched_data(data)
    assert len(points) == 1
    assert points[0]["title"] == "Test Pharmacy"
    assert points[0]["position"] == {"lat": 39.7, "lng": 30.5}


def test_get_map_points_from_pharmacies() -> None:
    class MockPharmacy:
        def __init__(self) -> None:
            self.location = Point(30.5, 39.7)
            self.name = "Test Pharmacy"
            self.address = "Test Address"
            self.distance = MagicMock()
            self.distance.m = 500

    points = get_map_points_from_pharmacies([MockPharmacy()])
    assert len(points) == 1
    assert points[0]["distance"] == 500
    assert points[0]["position"] == {"lat": 39.7, "lng": 30.5}


def test_order_data_by_distance() -> None:
    data = [
        {"travel_distance": 1000},
        {"travel_distance": 500},
        {"travel_distance": 1500},
    ]
    order_data_by_distance(data)
    assert data[0]["travel_distance"] == 500
    assert data[1]["travel_distance"] == 1000
    assert data[2]["travel_distance"] == 1500


def test_round_lat_lng() -> None:
    assert round_lat_lng(39.1234567, 30.1234567, 4) == (39.1235, 30.1235)


def test_extract_city_name_from_google_maps_response_compound_code() -> None:
    data = {
        "status": "OK",
        "plus_code": {"compound_code": "XF+VX Eskişehir, Turkey"},
        "results": [{}],  # Dummy result
    }
    assert (
        extract_city_name_from_google_maps_response(data) == "XF+VX Eskişehir, Turkey"
    )


def test_extract_city_name_from_google_maps_response_address_components() -> None:
    data = {
        "status": "OK",
        "plus_code": {},
        "results": [
            {
                "address_components": [
                    {"long_name": "Eskişehir", "types": ["administrative_area_level_1"]}
                ]
            }
        ],
    }
    assert extract_city_name_from_google_maps_response(data) == "Eskişehir"


def test_extract_city_name_from_google_maps_response_error() -> None:
    data = {"status": "ZERO_RESULTS", "results": []}
    with pytest.raises(
        ValueError, match="Unable to retrieve city name: status is not OK"
    ):
        extract_city_name_from_google_maps_response(data)


@patch("pharmacies.utils.utils.requests.get")
def test_get_city_name_from_location_istanbul(mock_get: MagicMock) -> None:
    get_city_name_from_location.cache_clear()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "plus_code": {"compound_code": "İstanbul, Turkey"},
        "results": [{}],  # Dummy result
    }
    mock_get.return_value = mock_response

    assert get_city_name_from_location(41.0, 28.0) == "istanbul"


@patch("pharmacies.utils.utils.requests.get")
def test_get_city_name_from_location_unknown(mock_get: MagicMock) -> None:
    get_city_name_from_location.cache_clear()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "plus_code": {"compound_code": "SomePlace, Turkey"},
        "results": [{}],  # Dummy result
    }
    mock_get.return_value = mock_response

    with pytest.raises(ValueError, match="Unknown city"):
        get_city_name_from_location(0, 0)


@patch("pharmacies.utils.utils.requests.get")
def test_get_distance_matrix_data(mock_get: MagicMock) -> None:
    from pharmacies.utils.utils import _get_distance_matrix_data

    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "OK", "rows": []}
    mock_get.return_value = mock_response

    data = _get_distance_matrix_data("39.7,30.5", "39.8,30.6")
    assert data["status"] == "OK"


@patch("pharmacies.utils.utils._get_distance_matrix_data")
def test_add_travel_distances_to_pharmacy_data(mock_get_dm: MagicMock) -> None:
    from pharmacies.utils.utils import add_travel_distances_to_pharmacy_data

    mock_get_dm.return_value = {
        "status": "OK",
        "rows": [
            {
                "elements": [
                    {
                        "status": "OK",
                        "distance": {"value": 1200},
                        "duration": {"value": 300},
                    }
                ]
            }
        ],
    }

    pharmacy_data = [{"position": {"lat": 39.8, "lng": 30.6}, "distance": 1000}]
    add_travel_distances_to_pharmacy_data(39.7, 30.5, pharmacy_data)

    assert pharmacy_data[0]["travel_distance"] == 1200
    assert pharmacy_data[0]["travel_duration"] == 300


def test_add_travel_distances_to_pharmacy_data_empty() -> None:
    from pharmacies.utils.utils import add_travel_distances_to_pharmacy_data

    with pytest.raises(
        ValueError, match="Cannot retrieve travel distances. Pharmacy data is empty!"
    ):
        add_travel_distances_to_pharmacy_data(39.7, 30.5, [])


@pytest.mark.django_db
class TestUtilsDB:
    def test_check_if_pharmacy_exists(self) -> None:
        from pharmacies.utils.utils import check_if_pharmacy_exists

        city = City.objects.create(name="Eskişehir")
        Pharmacy.objects.create(
            name="Eczane 1",
            phone="123",
            city=city,
            district="D1",
            location=Point(30, 39),
        )

        assert check_if_pharmacy_exists("Eczane 1", "123") is True
        assert check_if_pharmacy_exists("Eczane 2", "123") is False

    def test_add_scraped_data_to_db(self) -> None:
        from pharmacies.utils.utils import add_scraped_data_to_db

        city = City.objects.create(name="eskisehir")
        scraped_data = [
            {
                "name": "New Eczane",
                "address": "Address 1",
                "phone": "456",
                "district": "Odunpazarı",
                "coordinates": {"lat": 39.7, "lng": 30.5},
                "duty_start": datetime(2025, 12, 16, 18, 0, tzinfo=UTC),
                "duty_end": datetime(2025, 12, 17, 8, 0, tzinfo=UTC),
            }
        ]
        add_scraped_data_to_db(scraped_data, "eskisehir")

        assert Pharmacy.objects.filter(name="New Eczane", city=city).exists()
        pharmacy = Pharmacy.objects.get(name="New Eczane", city=city)
        assert pharmacy.phone == "456"

    def test_check_scraped_data_age_new(self) -> None:
        from pharmacies.utils.utils import ScrapedDataStatus, check_scraped_data_age

        city = City.objects.create(name="eskisehir")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Tuesday 10:00 - Open, should be NEW
        query_time = datetime(2025, 12, 16, 10, 0, tzinfo=UTC)
        assert check_scraped_data_age("eskisehir", query_time) == ScrapedDataStatus.NEW

    def test_check_scraped_data_age_old(self) -> None:
        from pharmacies.utils.utils import ScrapedDataStatus, check_scraped_data_age

        city = City.objects.create(name="eskisehir")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Tuesday 20:00 - Closed, last_scraped_at is None
        query_time = datetime(2025, 12, 16, 20, 0, tzinfo=UTC)
        assert check_scraped_data_age("eskisehir", query_time) == ScrapedDataStatus.OLD

        # Tuesday 20:00 - Closed, last_scraped_at is yesterday
        city.last_scraped_at = query_time - timedelta(days=1)
        city.save()
        assert check_scraped_data_age("eskisehir", query_time) == ScrapedDataStatus.OLD

    def test_get_nearest_pharmacies_on_duty(self) -> None:
        from pharmacies.utils.utils import get_nearest_pharmacies_on_duty

        city = City.objects.create(name="eskisehir")
        _ = Pharmacy.objects.create(
            name="On Duty Eczane",
            city=city,
            district="D1",
            location=Point(30.5, 39.7),
            duty_start=datetime(2025, 12, 16, 18, 0, tzinfo=UTC),
            duty_end=datetime(2025, 12, 17, 8, 0, tzinfo=UTC),
        )

        # Tuesday 22:00
        query_time = datetime(2025, 12, 16, 22, 0, tzinfo=UTC)

        # Mock add_travel_distances_to_pharmacy_data to avoid API call
        with patch(
            "pharmacies.utils.utils.add_travel_distances_to_pharmacy_data"
        ) as mock_add_travel:
            # We need to manually add travel_distance because the mock won't do it
            def side_effect(lat: float, lng: float, pharmacy_data: list[Any]) -> None:
                for p in pharmacy_data:
                    p["travel_distance"] = 100

            mock_add_travel.side_effect = side_effect

            results = get_nearest_pharmacies_on_duty(
                lat=39.7, lng=30.5, city="eskisehir", time=query_time
            )

            assert len(results) == 1
            assert results[0]["title"] == "On Duty Eczane"

    @patch("pharmacies.utils.utils.fetch_nearest_pharmacies")
    def test_get_nearest_pharmacies_open(self, mock_fetch: MagicMock) -> None:
        from pharmacies.utils.utils import get_nearest_pharmacies_open

        mock_fetch.return_value = [
            {
                "name": "Open Eczane",
                "geometry": {"location": {"lat": 39.7, "lng": 30.5}},
                "vicinity": "Some address",
            }
        ]

        with patch(
            "pharmacies.utils.utils.add_travel_distances_to_pharmacy_data"
        ) as mock_add_travel:

            def side_effect(lat: float, lng: float, pharmacy_data: list[Any]) -> None:
                for p in pharmacy_data:
                    p["travel_distance"] = 100

            mock_add_travel.side_effect = side_effect

            results = get_nearest_pharmacies_open(lat=39.7, lng=30.5)

            assert len(results) == 1
            assert results[0]["title"] == "Open Eczane"
