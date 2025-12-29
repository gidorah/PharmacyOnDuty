import time

from django.contrib.gis.geos import Point
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from pharmacies.models import City, Pharmacy
from pharmacies.utils.utils import add_scraped_data_to_db


class ScraperPerformanceTest(TestCase):
    def setUp(self) -> None:
        self.city = City.objects.create(name="benchmark_city")
        self.num_existing = 50
        self.num_new = 50

        # Create existing pharmacies
        pharmacies = []
        for i in range(self.num_existing):
            pharmacies.append(
                Pharmacy(
                    name=f"Pharmacy {i}",
                    address=f"Address {i}",
                    phone=f"123456789{i}",
                    location=Point(30.0, 40.0),
                    duty_start=timezone.now(),
                    duty_end=timezone.now(),
                    district="District 1",
                    city=self.city,
                )
            )
        Pharmacy.objects.bulk_create(pharmacies)

    def test_add_scraped_data_performance(self) -> None:
        # Prepare scraped data: half updating existing, half creating new
        scraped_data = []

        # Updates
        for i in range(self.num_existing):
            scraped_data.append(
                {
                    "name": f"Pharmacy {i}",
                    "phone": f"123456789{i}",
                    "address": f"Updated Address {i}",
                    "coordinates": {"lat": 40.0, "lng": 30.0},
                    "duty_start": timezone.now(),
                    "duty_end": timezone.now(),
                    "district": "District 1",
                }
            )

        # Inserts
        for i in range(self.num_existing, self.num_existing + self.num_new):
            scraped_data.append(
                {
                    "name": f"Pharmacy {i}",
                    "phone": f"123456789{i}",
                    "address": f"Address {i}",
                    "coordinates": {"lat": 40.0, "lng": 30.0},
                    "duty_start": timezone.now(),
                    "duty_end": timezone.now(),
                    "district": "District 1",
                }
            )

        print(
            f"\nProcessing {len(scraped_data)} items ({self.num_existing} updates, {self.num_new} inserts)..."
        )

        start_time = time.time()
        with CaptureQueriesContext(connection) as ctx:
            add_scraped_data_to_db(scraped_data, self.city.name)
        end_time = time.time()

        duration = end_time - start_time
        query_count = len(ctx.captured_queries)

        print(f"Time taken: {duration:.4f}s")
        print(f"Queries executed: {query_count}")

        # With optimized implementation:
        # 1 query to get City
        # 1 query to fetch existing pharmacies
        # 1 query for bulk_create
        # 1 query for bulk_update
        # Total ~4 queries regardless of input size

        expected_max_queries = 10
        self.assertLess(
            query_count,
            expected_max_queries,
            "Query count is too high, N+1 problem detected!",
        )
