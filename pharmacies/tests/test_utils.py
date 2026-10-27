from datetime import UTC, datetime, time, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.gis.geos import Point

from pharmacies.models import City, Pharmacy, WorkingSchedule
from pharmacies.utils.utils import (
    UnknownCityError,
    UpstreamGeocodingError,
    _parse_location_identifier,
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


def test_get_map_points_from_fetched_data_without_vicinity() -> None:
    data = [
        {
            "geometry": {"location": {"lat": 39.7, "lng": 30.5}},
            "name": "Test Pharmacy",
        }
    ]

    points = get_map_points_from_fetched_data(data)

    assert len(points) == 1
    assert points[0]["description"] == ""
    assert points[0]["address"] == ""


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
    assert _parse_location_identifier(data) == "XF+VX Eskişehir, Turkey"


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
    assert _parse_location_identifier(data) == "Eskişehir"


def test_extract_city_name_from_google_maps_response_error() -> None:
    data = {"status": "ZERO_RESULTS", "results": []}
    with pytest.raises(UnknownCityError, match="Unknown city"):
        _parse_location_identifier(data)


def test_parse_location_identifier_plus_code_none_returns_admin() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": None,
        "results": [
            {
                "address_components": [
                    {"long_name": "Ankara", "types": ["administrative_area_level_1"]}
                ]
            }
        ],
    }
    assert _parse_location_identifier(data) == "Ankara"


def test_parse_location_identifier_missing_address_components_falls_back() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": {"compound_code": "XF+VX Eskisehir, Turkey"},
        "results": [{"formatted_address": "Somewhere"}],
    }
    assert _parse_location_identifier(data) == "XF+VX Eskisehir, Turkey"


def test_parse_location_identifier_address_components_none_falls_back() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": {"compound_code": "XF+VX Eskisehir, Turkey"},
        "results": [{"address_components": None}],
    }
    assert _parse_location_identifier(data) == "XF+VX Eskisehir, Turkey"


def test_parse_location_identifier_water_only_raises_unknown_city() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": {},
        "results": [
            {
                "address_components": [
                    {"long_name": "Pacific Ocean", "types": ["natural_feature"]}
                ]
            }
        ],
    }
    with pytest.raises(UnknownCityError, match="Unknown city"):
        _parse_location_identifier(data)


def test_parse_location_identifier_request_denied_raises_upstream() -> None:
    data: dict[str, Any] = {"status": "REQUEST_DENIED", "results": []}
    with pytest.raises(UpstreamGeocodingError, match="Unable to retrieve city name"):
        _parse_location_identifier(data)


def test_parse_location_identifier_over_query_limit_raises_upstream() -> None:
    data: dict[str, Any] = {"status": "OVER_QUERY_LIMIT", "results": []}
    with pytest.raises(UpstreamGeocodingError, match="Unable to retrieve city name"):
        _parse_location_identifier(data)


def test_parse_location_identifier_scans_all_results() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": {"compound_code": "Plus Only, Turkey"},
        "results": [
            {"address_components": []},
            {
                "address_components": [
                    {"long_name": "Konya", "types": ["administrative_area_level_1"]}
                ]
            },
        ],
    }
    assert _parse_location_identifier(data) == "Konya"


def test_parse_location_identifier_prefers_admin_over_compound() -> None:
    data: dict[str, Any] = {
        "status": "OK",
        "plus_code": {"compound_code": "XF+VX Eskisehir, Turkey"},
        "results": [
            {
                "address_components": [
                    {"long_name": "Ankara", "types": ["administrative_area_level_1"]}
                ]
            }
        ],
    }
    assert _parse_location_identifier(data) == "Ankara"


def test_parse_errors_are_value_errors() -> None:
    assert issubclass(UnknownCityError, ValueError)
    assert issubclass(UpstreamGeocodingError, ValueError)


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
    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_from_location_istanbul(self, mock_get: MagicMock) -> None:
        City.objects.create(name="istanbul")
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
    def test_get_city_name_from_location_unknown(self, mock_get: MagicMock) -> None:
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
    def test_get_city_name_zero_results_raises_unknown_city(
        self, mock_get: MagicMock
    ) -> None:
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_get.return_value = mock_response

        with pytest.raises(UnknownCityError, match="Unknown city"):
            get_city_name_from_location(39.7, 30.5)

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_request_denied_raises_upstream(
        self, mock_get: MagicMock
    ) -> None:
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "results": [],
            "error_message": "Bad key",
        }
        mock_get.return_value = mock_response

        with pytest.raises(
            UpstreamGeocodingError, match="Unable to retrieve city name"
        ):
            get_city_name_from_location(39.7, 30.5)

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_over_query_limit_raises_upstream(
        self, mock_get: MagicMock
    ) -> None:
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OVER_QUERY_LIMIT",
            "results": [],
        }
        mock_get.return_value = mock_response

        with pytest.raises(
            UpstreamGeocodingError, match="Unable to retrieve city name"
        ):
            get_city_name_from_location(39.7, 30.5)

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_invalid_json_raises_upstream(
        self, mock_get: MagicMock
    ) -> None:
        from json import JSONDecodeError

        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.side_effect = JSONDecodeError("msg", "doc", 0)
        mock_get.return_value = mock_response

        with pytest.raises(
            UpstreamGeocodingError, match="Unable to retrieve city name"
        ):
            get_city_name_from_location(39.7, 30.5)

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_plus_code_none_returns_admin(
        self, mock_get: MagicMock
    ) -> None:
        City.objects.create(name="ankara")
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "plus_code": None,
            "results": [
                {
                    "address_components": [
                        {
                            "long_name": "Ankara",
                            "types": ["administrative_area_level_1"],
                        }
                    ]
                }
            ],
        }
        mock_get.return_value = mock_response

        assert get_city_name_from_location(39.9, 32.8) == "ankara"

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_water_only_raises_unknown_city(
        self, mock_get: MagicMock
    ) -> None:
        City.objects.create(name="eskisehir")
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "plus_code": {"compound_code": "X+G Pacific Ocean"},
            "results": [
                {
                    "address_components": [
                        {"long_name": "Pacific Ocean", "types": ["natural_feature"]}
                    ]
                }
            ],
        }
        mock_get.return_value = mock_response

        with pytest.raises(UnknownCityError, match="Unknown city"):
            get_city_name_from_location(0.0, -140.0)

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_scans_all_results(self, mock_get: MagicMock) -> None:
        City.objects.create(name="konya")
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "plus_code": {"compound_code": "Plus Only, Turkey"},
            "results": [
                {"address_components": []},
                {
                    "address_components": [
                        {
                            "long_name": "Konya",
                            "types": ["administrative_area_level_1"],
                        }
                    ]
                },
            ],
        }
        mock_get.return_value = mock_response

        assert get_city_name_from_location(37.8, 32.4) == "konya"

    @patch("pharmacies.utils.utils.requests.get")
    def test_get_city_name_prefers_admin_over_compound(
        self, mock_get: MagicMock
    ) -> None:
        City.objects.create(name="ankara")
        City.objects.create(name="eskisehir")
        get_city_name_from_location.cache_clear()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "plus_code": {"compound_code": "XF+VX Eskisehir, Turkey"},
            "results": [
                {
                    "address_components": [
                        {
                            "long_name": "Ankara",
                            "types": ["administrative_area_level_1"],
                        }
                    ]
                }
            ],
        }
        mock_get.return_value = mock_response

        assert get_city_name_from_location(39.9, 32.8) == "ankara"

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
            assert results[0]["address"] == ""
            assert results[0]["description"] == ""
            assert results[0]["travel_distance"] == 100
