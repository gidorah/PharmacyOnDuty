from collections.abc import Iterator
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from pharmacies.models import City, Pharmacy, ScraperConfig

URL = "/health/data/"


@pytest.fixture(autouse=True)
def _disable_ssl_redirect() -> Iterator[None]:
    """View tests hit the test client over HTTP; disable HTTPS redirects."""
    with override_settings(SECURE_SSL_REDIRECT=False):
        yield


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    """The endpoint is cache_page'd; keep tests independent."""
    cache.clear()
    yield
    cache.clear()


def _pharmacy(city: City, name: str, start_h: int, end_h: int) -> Pharmacy:
    now = timezone.now()
    return Pharmacy.objects.create(
        name=name,
        city=city,
        district="Center",
        location=Point(30.5, 39.7),
        duty_start=now + timedelta(hours=start_h),
        duty_end=now + timedelta(hours=end_h),
    )


@pytest.mark.django_db
class TestDataHealth:
    def test_shape_lists_every_city_with_exactly_three_keys(
        self, client: Client
    ) -> None:
        City.objects.create(name="alpha")
        City.objects.create(name="beta")

        response = client.get(URL)

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"cities", "time"}
        assert set(body["cities"]) == {"alpha", "beta"}
        for entry in body["cities"].values():
            assert set(entry) == {"last_scrape", "duty_now", "duty_next_12h"}

    def test_counts_duty_windows(self, client: Client) -> None:
        busy = City.objects.create(name="busy")
        City.objects.create(name="empty")
        _pharmacy(busy, "on duty now", -2, 10)
        _pharmacy(busy, "later today", 3, 20)
        _pharmacy(busy, "yesterday", -30, -6)
        _pharmacy(busy, "in 13h", 13, 30)

        cities = client.get(URL).json()["cities"]

        assert cities["busy"]["duty_now"] == 1
        assert cities["busy"]["duty_next_12h"] == 2
        assert cities["empty"] == {
            "last_scrape": None,
            "duty_now": 0,
            "duty_next_12h": 0,
        }

    def test_last_scrape(self, client: Client) -> None:
        City.objects.create(name="no-config")
        never = City.objects.create(name="never-ran")
        ran = City.objects.create(name="ran")
        ScraperConfig.objects.create(city=never, last_run=None)
        last_run = timezone.now() - timedelta(hours=1)
        ScraperConfig.objects.create(city=ran, last_run=last_run)

        cities = client.get(URL).json()["cities"]

        assert cities["no-config"]["last_scrape"] is None
        assert cities["never-ran"]["last_scrape"] is None
        assert cities["ran"]["last_scrape"] == last_run.isoformat()

    @pytest.mark.parametrize("method", ["post", "put", "delete"])
    def test_other_methods_not_allowed(self, client: Client, method: str) -> None:
        response = getattr(client, method)(URL)
        assert response.status_code == 405

    def test_makes_no_outbound_calls(self, client: Client) -> None:
        City.objects.create(name="alpha")
        with (
            patch("pharmacies.views.requests.get") as get,
            patch("pharmacies.views.requests.post") as post,
            patch("requests.Session.request") as session_request,
        ):
            response = client.get(URL)

        assert response.status_code == 200
        get.assert_not_called()
        post.assert_not_called()
        session_request.assert_not_called()

    def test_single_query_regardless_of_city_count(
        self, client: Client, django_assert_num_queries: Any
    ) -> None:
        for name in ("a", "b", "c"):
            City.objects.create(name=name)
        with django_assert_num_queries(1):
            response = client.get(URL)
        assert len(response.json()["cities"]) == 3

    def test_not_rate_limited(self, client: Client) -> None:
        City.objects.create(name="alpha")
        with patch("pharmacies.views.is_rate_limited", return_value=True) as limited:
            response = client.get(URL)
        assert response.status_code == 200
        limited.assert_not_called()

    def test_answer_is_cached_for_60_seconds(self, client: Client) -> None:
        city = City.objects.create(name="alpha")

        first = client.get(URL)
        _pharmacy(city, "on duty now", -1, 5)
        second = client.get(URL)

        assert "max-age=60" in first["Cache-Control"]
        assert second.json() == first.json()
        assert second.json()["cities"]["alpha"]["duty_now"] == 0

        cache.clear()
        assert client.get(URL).json()["cities"]["alpha"]["duty_now"] == 1


@pytest.mark.django_db
class TestHealthIsHidden:
    def test_not_in_sitemap(self, client: Client) -> None:
        response = client.get(reverse("django.contrib.sitemaps.views.sitemap"))
        assert response.status_code == 200
        assert "/health/" not in response.content.decode()

    def test_robots_disallows_health(self, client: Client) -> None:
        response = client.get("/robots.txt")
        assert "Disallow: /health/" in response.content.decode()
