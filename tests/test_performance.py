import json
import time
from typing import Any

import pytest
from django.urls import reverse

from pharmacies.utils.utils import add_scraped_data_to_db
from tests.helpers import generate_synthetic_pharmacies


@pytest.mark.django_db
class TestPerformance:
    def setup_method(self, method: Any) -> None:
        from django.core.management import call_command

        # 1. Seed base city data
        call_command("seed_cities")

        # 2. Generate and load 1500 synthetic pharmacies
        # (500 per city for Istanbul, Ankara, Eskisehir)
        print("Generating 1500 synthetic pharmacies...")
        synthetic_data = generate_synthetic_pharmacies(count=1500)

        # Group by city for ingestion
        city_groups: dict[str, list[dict[str, Any]]] = {}
        for item in synthetic_data:
            c = item["city"]
            if c not in city_groups:
                city_groups[c] = []
            city_groups[c].append(item)

        # Ingest data
        for city_name, items in city_groups.items():
            add_scraped_data_to_db(items, city_name)
        print("Data ingestion complete.")

    def test_spatial_query_performance_under_load(self, client: Any) -> None:
        """
        Verifies that finding nearest pharmacies remains fast (< 500ms)
        even with a populated database (1500+ records).
        """
        # Test location: Istanbul - Kadikoy (Central)
        lat = 40.9908
        lng = 29.0293

        # Warm-up request (optional, but good for JIT/Caching)
        client.post(
            reverse("pharmacies:get_pharmacy_points"),
            data=json.dumps({"lat": lat, "lng": lng}),
            content_type="application/json",
        )

        durations = []
        iterations = 10

        for _ in range(iterations):
            start_time = time.time()
            response = client.post(
                reverse("pharmacies:get_pharmacy_points"),
                data=json.dumps({"lat": lat, "lng": lng}),
                content_type="application/json",
            )
            duration = (time.time() - start_time) * 1000
            durations.append(duration)

            assert response.status_code == 200
            data = response.json()
            # We expect results since we seeded data around the city centers
            assert len(data.get("points", [])) > 0

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)

        print(f"\nPerformance Stats ({iterations} iterations):")
        print(f"  Avg: {avg_duration:.2f}ms")
        print(f"  Max: {max_duration:.2f}ms")

        # Assertion: Average under 200ms, Max under 500ms
        assert avg_duration < 200, f"Average response too slow: {avg_duration:.2f}ms"
        assert max_duration < 500, f"Max response too slow: {max_duration:.2f}ms"
