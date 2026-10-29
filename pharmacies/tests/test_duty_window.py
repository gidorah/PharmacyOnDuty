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


def _utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


@pytest.mark.parametrize(
    ("now", "start", "end"),
    [
        # Eve of Republic Day (Wed 28 Oct 2026): from 13:00 TRT (10:00 UTC)
        (_utc(2026, 10, 28, 12), _utc(2026, 10, 28, 10), _utc(2026, 10, 29, 6)),
        (_utc(2026, 10, 28, 20), _utc(2026, 10, 28, 10), _utc(2026, 10, 29, 6)),
        # Republic Day (Thu 29 Oct 2026) 03:00: still the eve's window
        (_utc(2026, 10, 29, 3), _utc(2026, 10, 28, 10), _utc(2026, 10, 29, 6)),
        # The holiday itself behaves like a Sunday
        (_utc(2026, 10, 29, 6), _utc(2026, 10, 29, 6), _utc(2026, 10, 30, 6)),
        (_utc(2026, 10, 29, 13), _utc(2026, 10, 29, 6), _utc(2026, 10, 30, 6)),
        (_utc(2026, 10, 29, 20), _utc(2026, 10, 29, 6), _utc(2026, 10, 30, 6)),
        # The morning after, before the Friday opening is over: holiday window
        (_utc(2026, 10, 30, 5), _utc(2026, 10, 29, 6), _utc(2026, 10, 30, 6)),
        # Ordinary Thursday: as always
        (_utc(2026, 11, 5, 14), _utc(2026, 11, 5, 15, 30), _utc(2026, 11, 6, 6)),
        # Tuesday before Wednesday's holiday (19 May 2026): ends at 06:00
        (_utc(2026, 5, 18, 14), _utc(2026, 5, 18, 15, 30), _utc(2026, 5, 19, 6)),
        # Friday before a Saturday holiday (1 May 2027): ends at 06:00, not 07:00
        (_utc(2027, 4, 30, 14), _utc(2027, 4, 30, 15, 30), _utc(2027, 5, 1, 6)),
        # Holiday on a Saturday: 06:00 to 06:00, not Saturday's hours
        (_utc(2027, 5, 1, 6, 30), _utc(2027, 5, 1, 6), _utc(2027, 5, 2, 6)),
        # Holiday followed by a Saturday (Fri 1 Jan 2027): ends at its opening
        (_utc(2027, 1, 1, 12), _utc(2027, 1, 1, 6), _utc(2027, 1, 2, 7)),
        # Kurban Bayramı 2027, Saturday eve (15 May): 13:00 TRT, not 15:00 UTC
        (_utc(2027, 5, 15, 12), _utc(2027, 5, 15, 10), _utc(2027, 5, 16, 6)),
        # Middle day of Kurban Bayramı 2027 (Mon 17 May)
        (_utc(2027, 5, 17, 12), _utc(2027, 5, 17, 6), _utc(2027, 5, 18, 6)),
        # Last day (Wed 19 May) evening runs to 06:00 on Thursday
        (_utc(2027, 5, 19, 20), _utc(2027, 5, 19, 6), _utc(2027, 5, 20, 6)),
        # Morning after the last day (Thu 20 May), 05:00: still the holiday
        (_utc(2027, 5, 20, 5), _utc(2027, 5, 19, 6), _utc(2027, 5, 20, 6)),
        # Thursday 20 May afternoon: ordinary day again
        (_utc(2027, 5, 20, 14), _utc(2027, 5, 20, 15, 30), _utc(2027, 5, 21, 6)),
    ],
)
def test_window_around_public_holidays_and_eves(
    schedule: WorkingSchedule, now: datetime, start: datetime, end: datetime
) -> None:
    assert _window(now) == (start, end)


def _uncovered_by_all_scrapes(
    schedule: WorkingSchedule, sweep_start: datetime, days: int
) -> list[str]:
    windows = {
        scrape: _window(scrape, schedule.city.name)
        for scrape in (
            sweep_start + timedelta(hours=hours) for hours in range(-48, days * 24 + 1)
        )
    }
    uncovered = []
    for step in range(days * 24 * 4):
        t = sweep_start + timedelta(minutes=15 * step)
        if schedule.is_open(t):
            continue
        if not any(
            start <= t <= end for scrape, (start, end) in windows.items() if scrape <= t
        ):
            uncovered.append(t.strftime("%d %a %H:%M"))
    return uncovered


def _uncovered_by_the_latest_scrape(
    schedule: WorkingSchedule, sweep_start: datetime, days: int
) -> list[str]:
    uncovered = []
    for step in range(days * 24 * 4):
        t = sweep_start + timedelta(minutes=15 * step)
        if schedule.is_open(t):
            continue
        latest_scrape = t.replace(minute=0)
        if latest_scrape == t:
            latest_scrape -= timedelta(hours=1)
        start, end = _window(latest_scrape, schedule.city.name)
        if not start <= t <= end:
            uncovered.append(t.strftime("%d %a %H:%M"))
    return uncovered


HOLIDAY_WEEKS = [
    pytest.param(_utc(2026, 10, 26, 0), id="republic-day-2026"),
    pytest.param(_utc(2027, 5, 12, 0), id="kurban-bayrami-2027"),
]


@pytest.mark.parametrize("city_name", CITIES)
@pytest.mark.parametrize("sweep_start", HOLIDAY_WEEKS)
def test_hourly_scrapes_cover_holiday_weeks(
    seeded_cities: None, city_name: str, sweep_start: datetime
) -> None:
    schedule = WorkingSchedule.objects.get(city__name=city_name)

    assert _uncovered_by_all_scrapes(schedule, sweep_start, 10) == []


@pytest.mark.parametrize("city_name", CITIES)
@pytest.mark.parametrize("sweep_start", HOLIDAY_WEEKS)
def test_hourly_scrapes_of_the_same_pharmacies_cover_holiday_weeks(
    seeded_cities: None, city_name: str, sweep_start: datetime
) -> None:
    schedule = WorkingSchedule.objects.get(city__name=city_name)

    assert _uncovered_by_the_latest_scrape(schedule, sweep_start, 10) == []
