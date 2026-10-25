"""
Per-client-IP rate limiting backed by the shared Redis cache.

Uses a fixed-window counter stored in the ``"ratelimit"`` cache alias so the
limit is shared across gunicorn workers and processes.
"""

import logging
import time

from django.conf import settings
from django.core.cache import caches
from django.http import HttpRequest

logger = logging.getLogger(__name__)

RATE_PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_rate(rate: str) -> tuple[int, int]:
    """Parse a rate such as ``"30/m"`` into ``(limit, period_seconds)``."""
    count, sep, unit = rate.partition("/")
    if not sep or unit not in RATE_PERIODS or not count.isdigit():
        raise ValueError(f"Invalid rate: {rate!r}")
    limit = int(count)
    if limit <= 0:
        raise ValueError(f"Invalid rate: {rate!r}")
    return limit, RATE_PERIODS[unit]


def get_client_ip(request: HttpRequest) -> str:
    """
    Return the client IP used as the rate-limit key.

    With no trusted proxies, ``REMOTE_ADDR`` is used (it cannot be spoofed via
    headers). With N trusted proxies, the Nth-from-right ``X-Forwarded-For``
    entry is used, falling back to ``REMOTE_ADDR`` if there are too few entries.
    """
    remote_addr = str(request.META.get("REMOTE_ADDR", ""))
    proxy_count: int = settings.RATELIMIT_TRUSTED_PROXY_COUNT
    if proxy_count <= 0:
        return remote_addr

    forwarded_for = str(request.META.get("HTTP_X_FORWARDED_FOR", ""))
    entries = [entry.strip() for entry in forwarded_for.split(",") if entry.strip()]
    if len(entries) < proxy_count:
        return remote_addr
    return entries[-proxy_count]


def is_rate_limited(request: HttpRequest, scope: str, rate: str) -> bool:
    """
    Count this request against ``rate`` and return True if it is over the limit.

    Fails open (returns False) if the cache backend is unavailable.
    """
    limit, period = parse_rate(rate)
    window = int(time.time()) // period
    key = f"{scope}:{get_client_ip(request)}:{window}"
    cache = caches["ratelimit"]

    try:
        cache.add(key, 0, timeout=period)
        try:
            count = cache.incr(key)
        except ValueError:
            # Key expired between add() and incr().
            cache.add(key, 1, timeout=period)
            count = 1
    except Exception:
        logger.exception("Rate limit cache unavailable; allowing request")
        return False

    return count > limit
