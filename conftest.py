"""Project-wide pytest fixtures."""

from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import caches
from django.test.utils import override_settings


@pytest.fixture(autouse=True)
def _isolated_ratelimit_cache() -> Iterator[None]:
    """
    Swap the Redis-backed rate-limit cache for an in-memory one in tests.

    Keeps tests from sharing counters (and from flushing the shared Redis,
    which is also the Celery broker) while leaving the default cache as is.
    """
    test_caches: dict[str, dict[str, Any]] = {
        **settings.CACHES,
        "ratelimit": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "ratelimit-tests",
        },
    }
    with override_settings(CACHES=test_caches):
        caches["ratelimit"].clear()
        yield
        caches["ratelimit"].clear()
