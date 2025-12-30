import json
import time
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone

with open("tests/fixtures/location_scenarios.json") as f:
    LOCATION_SCENARIOS = json.load(f)


@pytest.fixture
def api_snapshots() -> dict[str, Any]:
    with open("tests/fixtures/google_api_snapshots.json") as f:
        data: dict[str, Any] = json.load(f)
        return data


@pytest.fixture
def fabricated_pharmacies() -> list[dict[str, Any]]:
    with open("tests/fixtures/fabricated_pharmacies.json") as f:
        data: list[dict[str, Any]] = json.load(f)
        return data


@pytest.mark.django_db
class TestLocationCoverage:
    def setup_method(self, method: Any) -> None:
        from django.core.management import call_command

        call_command("seed_cities")

        from datetime import timedelta
        from typing import Any

        from pharmacies.utils.utils import add_scraped_data_to_db

        with open("tests/fixtures/fabricated_pharmacies.json") as f:
            fabricated_data = json.load(f)

        city_groups: dict[str, list[dict[str, Any]]] = {}
        for item in fabricated_data:
            c = item["city"]
            if c not in city_groups:
                city_groups[c] = []

            item_copy = item.copy()
            now = timezone.now()
            item_copy["duty_start"] = now - timedelta(hours=1)
            item_copy["duty_end"] = now + timedelta(hours=24)

            city_groups[c].append(item_copy)

        for city_name, items in city_groups.items():
            add_scraped_data_to_db(items, city_name)

    def test_smoke_scenarios(
        self, client: Any, api_snapshots: dict[str, Any], mock_google_maps: Any
    ) -> None:
        for scenario in LOCATION_SCENARIOS:
            lat = scenario["latitude"]
            lng = scenario["longitude"]

            start_time = time.time()
            response = client.post(
                reverse("pharmacies:get_pharmacy_points"),
                data=json.dumps({"lat": lat, "lng": lng}),
                content_type="application/json",
            )
            duration = (time.time() - start_time) * 1000

            assert (
                duration < 500
            ), f"Slow response for {scenario['description']}: {duration:.2f}ms"

            if scenario["expected_behavior"] == "should_return_pharmacy":
                assert (
                    response.status_code == 200
                ), f"Failed for {scenario['description']} (Expected 200, got {response.status_code})"
                data = response.json()
                assert (
                    "points" in data
                ), f"No points returned for {scenario['description']}"
                points = data["points"]
                assert (
                    len(points) > 0
                ), f"Empty points list for {scenario['description']}"

                prev_distance = -1
                for point in points:
                    assert (
                        "travel_distance" in point
                    ), f"Missing travel_distance in {point}"
                    assert (
                        "travel_duration" in point
                    ), f"Missing travel_duration in {point}"

                    curr_distance = point["travel_distance"]
                    assert (
                        curr_distance >= prev_distance
                    ), f"Points not sorted by distance for {scenario['description']}"
                    prev_distance = curr_distance
            else:
                assert (
                    response.status_code in [200, 400]
                ), f"Unexpected status {response.status_code} for {scenario['description']}"
