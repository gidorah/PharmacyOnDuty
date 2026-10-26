import json
import math
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.utils import timezone

from pharmacies.utils.pharmacy_fetch import _fetch_pharmacy_data
from pharmacies.utils.utils import (
    _get_distance_matrix_data,
    get_city_name_from_location,
)


def _normalize_coordinates(coordinates: str) -> str:
    """Make "0,0" and "0.0,0.0" the same snapshot key."""
    return ",".join(str(float(part)) for part in coordinates.split(","))


def _clear_google_api_caches() -> None:
    get_city_name_from_location.cache_clear()
    _get_distance_matrix_data.cache_clear()
    _fetch_pharmacy_data.cache_clear()


@pytest.fixture
def google_snapshots() -> dict[str, Any]:
    with open("tests/fixtures/google_api_snapshots.json") as f:
        data: dict[str, Any] = json.load(f)
        return data


class MockResponse:
    def __init__(self, json_data: dict[str, Any], status_code: int = 200) -> None:
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self) -> dict[str, Any]:
        return self.json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")


def _generated_distance_matrix(origins: str, destinations: str) -> dict[str, Any]:
    """
    Build an OK Distance Matrix payload with one element per destination.

    Travel distance is the straight-line distance times a road factor of 1.3;
    travel time assumes 30 km/h, so the values are deterministic.
    """
    origin_lat, origin_lng = (math.radians(float(p)) for p in origins.split(","))
    elements = []
    for destination in destinations.split("|"):
        lat, lng = (math.radians(float(p)) for p in destination.split(","))
        haversine = (
            math.sin((lat - origin_lat) / 2) ** 2
            + math.cos(origin_lat)
            * math.cos(lat)
            * math.sin((lng - origin_lng) / 2) ** 2
        )
        straight_m = 2 * 6_371_000 * math.asin(math.sqrt(haversine))
        distance_m = round(straight_m * 1.3)
        duration_s = round(distance_m / (30 / 3.6))
        elements.append(
            {
                "distance": {
                    "text": f"{distance_m / 1000:.1f} km",
                    "value": distance_m,
                },
                "duration": {
                    "text": f"{max(1, round(duration_s / 60))} mins",
                    "value": duration_s,
                },
                "status": "OK",
            }
        )
    return {
        "destination_addresses": destinations.split("|"),
        "origin_addresses": [origins],
        "rows": [{"elements": elements}],
        "status": "OK",
    }


def _google_maps_mock(
    google_snapshots: dict[str, Any], generate_distances: bool
) -> Generator[Any]:
    snapshots: dict[str, Any] = {}
    for snapshot_key, payload in google_snapshots.items():
        kind, _, coordinates = snapshot_key.partition(":")
        snapshots[f"{kind}:{_normalize_coordinates(coordinates)}"] = payload

    def side_effect(
        url: str, params: dict[str, Any] | None = None, timeout: float | None = None
    ) -> Any:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        if "geocode" in parsed_url.path:
            if "latlng" in query_params:
                latlng_part = query_params["latlng"][0]
                key = f"geocode:{_normalize_coordinates(latlng_part)}"
                if key in snapshots:
                    return MockResponse(snapshots[key])

        elif "distancematrix" in parsed_url.path:
            if "origins" in query_params:
                origins_part = query_params["origins"][0]
                if generate_distances and "destinations" in query_params:
                    return MockResponse(
                        _generated_distance_matrix(
                            origins_part, query_params["destinations"][0]
                        )
                    )
                key = f"distancematrix:{_normalize_coordinates(origins_part)}"
                if key in snapshots:
                    return MockResponse(snapshots[key])

        print(f"WARNING: No snapshot found for URL: {url}")
        return MockResponse(
            {"status": "REQUEST_DENIED", "error_message": "No snapshot found"}, 200
        )

    # Cached Google lookups would otherwise leak between tests and skip the mock.
    _clear_google_api_caches()
    with patch("requests.get", side_effect=side_effect) as mock_get:
        yield mock_get
    _clear_google_api_caches()


@pytest.fixture
def mock_google_maps(google_snapshots: dict[str, Any]) -> Generator[Any]:
    yield from _google_maps_mock(google_snapshots, generate_distances=False)


@pytest.fixture
def mock_google_maps_generated_distances(
    google_snapshots: dict[str, Any],
) -> Generator[Any]:
    """
    Like mock_google_maps, but Distance Matrix answers every destination sent.

    For tests whose pharmacies are random, so no recorded snapshot can match.
    Geocoding still comes from the snapshots.
    """
    yield from _google_maps_mock(google_snapshots, generate_distances=True)


@pytest.fixture
def off_hours_now() -> Generator[datetime]:
    """
    Pin timezone.now() to the next 02:00 UTC, outside every city's working hours.

    It falls inside the duty window seeded at the real now (now-1h .. now+24h),
    so the view takes the on-duty path instead of the Google Places one.
    """
    real_now = timezone.now()
    pinned = real_now.replace(hour=2, minute=0, second=0, microsecond=0)
    if pinned <= real_now:
        pinned += timedelta(days=1)
    with patch("django.utils.timezone.now", return_value=pinned):
        yield pinned
