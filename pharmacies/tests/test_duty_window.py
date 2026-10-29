from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta
from unittest.mock import patch

import pytest

from pharmacies.models import City, WorkingSchedule
from pharmacies.utils.duty_window import get_duty_window

pytestmark = pytest.mark.django_db

CITIES = ["istanbul", "ankara"]


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    """A moment in November 2026 (the 2nd is a Monday), UTC."""
    return datetime(2026, 11, day, hour, minute, tzinfo=UTC)


def _make_schedule(
    city_name: str,
    weekday_end: time = time(15, 30),
) -> WorkingSchedule:
    city = City.objects.create(name=city_name)
    return WorkingSchedule.objects.create(
        city=city,
        weekday_start=time(5, 30),
        weekday_end=weekday_end,
        saturday_start=time(7, 0),
        saturday_end=time(15, 0),
    )


@pytest.fixture
def schedule() -> WorkingSchedule:
    return _make_schedule("istanbul")


def _window(now: datetime, city_name: str = "istanbul") -> tuple[datetime, datetime]:
    with patch("pharmacies.utils.duty_window.timezone.now", return_value=now):
        return get_duty_window(city_name)


@pytest.mark.parametrize(
    ("now", "start", "end"),
    [
        # Tuesday afternoon: from weekday closing to 06:00 next day
        (_at(3, 14), _at(3, 15, 30), _at(4, 6)),
        # Tuesday 05:00: still Monday's window
        (_at(3, 5), _at(2, 15, 30), _at(3, 6)),
        # Friday: runs to Saturday's opening
        (_at(6, 14), _at(6, 15, 30), _at(7, 7)),
        # Saturday 05:00: still Friday's window
        (_at(7, 5), _at(6, 15, 30), _at(7, 7)),
        # Saturday rolls over at the opening (07:00), not at 06:00
        (_at(7, 6), _at(6, 15, 30), _at(7, 7)),
        (_at(7, 6, 30), _at(6, 15, 30), _at(7, 7)),
        (_at(7, 7), _at(7, 15), _at(8, 6)),
        (_at(7, 20), _at(7, 15), _at(8, 6)),
        # Sunday after rollover: 06:00 Sunday to 06:00 Monday
        (_at(8, 10), _at(8, 6), _at(9, 6)),
        # Sunday before rollover: still Saturday's window
        (_at(8, 3), _at(7, 15), _at(8, 6)),
        # Monday 03:00: Sunday's window
        (_at(9, 3), _at(8, 6), _at(9, 6)),
    ],
)
def test_window_with_seeded_hours(
    schedule: WorkingSchedule, now: datetime, start: datetime, end: datetime
) -> None:
    assert _window(now) == (start, end)


def test_window_follows_the_cities_weekday_closing_time() -> None:
    _make_schedule("ankara", weekday_end=time(16, 30))

    assert _window(_at(3, 14), "ankara") == (_at(3, 16, 30), _at(4, 6))


@pytest.fixture
def seeded_cities() -> Iterator[None]:
    for name in CITIES:
        _make_schedule(name)
    yield


@pytest.mark.parametrize("city_name", CITIES)
def test_hourly_scrapes_cover_the_whole_week(
    seeded_cities: None, city_name: str
) -> None:
    schedule = WorkingSchedule.objects.get(city__name=city_name)
    sweep_start = _at(1, 0)  # Sunday
    steps = 8 * 24 * 4

    windows: dict[datetime, tuple[datetime, datetime]] = {}
    for hours in range(-48, 8 * 24 + 1):
        scrape = sweep_start + timedelta(hours=hours)
        windows[scrape] = _window(scrape, city_name)

    uncovered = []
    for step in range(steps):
        t = sweep_start + timedelta(minutes=15 * step)
        if schedule.is_open(t):
            continue
        if not any(
            start <= t <= end for scrape, (start, end) in windows.items() if scrape <= t
        ):
            uncovered.append(t.strftime("%a %H:%M"))

    assert uncovered == []


@pytest.mark.parametrize("city_name", CITIES)
def test_hourly_scrapes_of_the_same_pharmacies_cover_the_whole_week(
    seeded_cities: None, city_name: str
) -> None:
    """Worst case: every scrape lists the same pharmacies, so ingest keeps
    only the window of the latest scrape."""
    schedule = WorkingSchedule.objects.get(city__name=city_name)
    sweep_start = _at(1, 0)  # Sunday
    steps = 8 * 24 * 4

    uncovered = []
    for step in range(steps):
        t = sweep_start + timedelta(minutes=15 * step)
        if schedule.is_open(t):
            continue
        # A scrape at the full hour is still running at that very instant.
        latest_scrape = t.replace(minute=0)
        if latest_scrape == t:
            latest_scrape -= timedelta(hours=1)
        start, end = _window(latest_scrape, city_name)
        if not start <= t <= end:
            uncovered.append(t.strftime("%a %H:%M"))

    assert uncovered == []
