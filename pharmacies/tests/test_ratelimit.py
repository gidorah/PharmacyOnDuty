import json
from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext, override_settings
from django.urls import reverse

import PharmacyOnDuty.settings as project_settings
from pharmacies.ratelimit import get_client_ip, is_rate_limited, parse_rate

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

URL_NAME = "pharmacies:get_pharmacy_points"


@pytest.fixture(autouse=True)
def _disable_ssl_redirect() -> Iterator[None]:
    """View tests hit the test client over HTTP; disable HTTPS redirects."""
    with override_settings(SECURE_SSL_REDIRECT=False):
        yield


def _post(
    client: Client, remote_addr: str = "127.0.0.1"
) -> "_MonkeyPatchedWSGIResponse":
    # Missing "lng" -> 400 from normal handling, proving pass-through.
    return client.post(
        reverse(URL_NAME),
        data=json.dumps({"lat": 39.7}),
        content_type="application/json",
        REMOTE_ADDR=remote_addr,
    )


class TestSettings:
    def test_default_rate_is_30_per_minute(self) -> None:
        assert project_settings.PHARMACY_POINTS_RATE_LIMIT == "30/m"

    def test_ratelimit_cache_is_redis_backed(self) -> None:
        backend = project_settings.CACHES["ratelimit"]["BACKEND"]
        assert backend == "django_redis.cache.RedisCache"

    def test_default_cache_is_unchanged_locmem(self) -> None:
        backend = project_settings.CACHES["default"]["BACKEND"]
        assert backend == "django.core.cache.backends.locmem.LocMemCache"

    def test_tests_use_in_memory_ratelimit_cache(self) -> None:
        assert isinstance(caches["ratelimit"], LocMemCache)


class TestParseRate:
    @pytest.mark.parametrize(
        ("rate", "expected"),
        [
            ("30/m", (30, 60)),
            ("5/s", (5, 1)),
            ("100/h", (100, 3600)),
            ("1000/d", (1000, 86400)),
        ],
    )
    def test_valid(self, rate: str, expected: tuple[int, int]) -> None:
        assert parse_rate(rate) == expected

    @pytest.mark.parametrize("rate", ["", "30", "30/x", "abc/m", "-1/m", "0/m"])
    def test_invalid(self, rate: str) -> None:
        with pytest.raises(ValueError):
            parse_rate(rate)


class TestGetClientIp:
    def test_no_proxy_ignores_forwarded_for(self, rf: RequestFactory) -> None:
        request = rf.post("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")
        with override_settings(RATELIMIT_TRUSTED_PROXY_COUNT=0):
            assert get_client_ip(request) == "10.0.0.1"

    def test_one_proxy_uses_last_forwarded_entry(self, rf: RequestFactory) -> None:
        request = rf.post(
            "/",
            REMOTE_ADDR="172.16.0.1",
            HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.7",
        )
        with override_settings(RATELIMIT_TRUSTED_PROXY_COUNT=1):
            assert get_client_ip(request) == "203.0.113.7"

    def test_too_few_entries_falls_back_to_remote_addr(
        self, rf: RequestFactory
    ) -> None:
        request = rf.post(
            "/", REMOTE_ADDR="172.16.0.1", HTTP_X_FORWARDED_FOR="203.0.113.7"
        )
        with override_settings(RATELIMIT_TRUSTED_PROXY_COUNT=2):
            assert get_client_ip(request) == "172.16.0.1"


class TestPharmacyPointsRateLimit:
    @override_settings(PHARMACY_POINTS_RATE_LIMIT="3/m")
    def test_under_limit_passes_then_429(self, client: Client) -> None:
        for _ in range(3):
            response = _post(client)
            assert response.status_code == 400

        response = _post(client)
        assert response.status_code == 429
        assert response.json() == {
            "error": "Too many requests. Please try again later."
        }

    @pytest.mark.django_db
    @override_settings(PHARMACY_POINTS_RATE_LIMIT="1/m")
    @patch("pharmacies.views.get_city_name_from_location")
    def test_limited_request_skips_geocoding_and_db(
        self, mock_get_city: MagicMock, client: Client
    ) -> None:
        url = reverse(URL_NAME)
        payload = json.dumps({"lat": 39.7, "lng": 30.5})
        _post(client)  # consume the single allowed request

        with CaptureQueriesContext(connection) as queries:
            response = client.post(url, data=payload, content_type="application/json")

        assert response.status_code == 429
        mock_get_city.assert_not_called()
        assert len(queries.captured_queries) == 0

    @override_settings(PHARMACY_POINTS_RATE_LIMIT="1/m")
    def test_ips_are_counted_separately(self, client: Client) -> None:
        assert _post(client, "10.0.0.1").status_code == 400
        assert _post(client, "10.0.0.1").status_code == 429
        assert _post(client, "10.0.0.2").status_code == 400

    def test_cache_failure_fails_open(self, rf: RequestFactory) -> None:
        request = rf.post("/", REMOTE_ADDR="10.0.0.1")
        with patch.object(
            caches["ratelimit"], "add", side_effect=ConnectionError("redis down")
        ):
            for _ in range(3):
                assert not is_rate_limited(request, "pharmacy_points", "1/m")
