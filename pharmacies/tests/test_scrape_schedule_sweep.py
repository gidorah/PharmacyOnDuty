"""
Sweep the scrape schedule against the duty window (issue #297).

The scrape times come from the `PeriodicTask` rows `WorkingSchedule.save()` writes
plus the hourly interval scrape at :55. Each scrape runs the real Celery task with
the clock patched and the scrapers fed recorded pages, so the database after the
latest finished scrape is the state the visitor sees.
"""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, time, timedelta
from functools import cache
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from django_celery_beat.models import PeriodicTask
from requests.cookies import RequestsCookieJar

from pharmacies.models import City, WorkingSchedule
from pharmacies.tasks import run_scraper
from pharmacies.utils.duty_window import get_duty_window

FIXTURES = Path(__file__).parent / "fixtures"
ANKARA_MODULE = "pharmacies.utils.ankaraeo_scraper"
ISTANBUL_MODULE = "pharmacies.utils.istanbul_edevlet_scraper"
STEP = timedelta(minutes=15)
WARM_UP = timedelta(days=2)
CITIES = ["istanbul", "ankara"]
WEEKS = {
    "ordinary week": datetime(2026, 11, 2, tzinfo=UTC),
    "week of 2026-10-29": datetime(2026, 10, 26, tzinfo=UTC),
}


@cache
def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@cache
def _ankara_payload() -> Any:
    return json.loads(_text("ankaraeo_getpharmacies.json"))


def _response(text: str = "", payload: Any = None) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.is_redirect = False
    response.headers = {"Content-Type": "text/html; charset=UTF-8"}
    response.raise_for_status.return_value = None
    response.text = text
    response.json.return_value = payload
    return response


def _get(url: str, **_: Any) -> MagicMock:
    """Both scrapers call the one `requests.get`; answer by URL."""
    if url.startswith("https://www.aeo.org.tr/"):
        return _response(payload=_ankara_payload())
    name = "edevlet_map_1.html" if url.endswith("index=1") else "edevlet_map_0.html"
    return _response(_text(name))


def _istanbul_session() -> MagicMock:
    session = MagicMock()
    jar = RequestsCookieJar()
    jar.set("TURKIYESESSIONID", "abc")
    session.cookies = jar
    session.get.return_value = _response(_text("edevlet_form.html"))
    session.post.return_value = _response(_text("edevlet_result.html"))
    return session


@pytest.fixture(autouse=True)
def _recorded_pages() -> Iterator[None]:
    """Feed both scrapers their recorded pages; nothing reaches the network."""
    with (
        patch("requests.get", side_effect=_get),
        patch(f"{ISTANBUL_MODULE}.requests.Session") as session_class,
    ):
        session_class.side_effect = _istanbul_session
        yield


@pytest.fixture(autouse=True)
def _no_ssl_redirect() -> Iterator[None]:
    with override_settings(SECURE_SSL_REDIRECT=False):
        yield


def _seed(city_name: str) -> City:
    """Seed a city as `seed_cities` does: UTC hours of 08:30-18:30 / 10:00-18:00."""
    city = City.objects.create(name=city_name)
    WorkingSchedule.objects.create(
        city=city,
        weekday_start=time(5, 30),
        weekday_end=time(15, 30),
        saturday_start=time(7, 0),
        saturday_end=time(15, 0),
    )
    return city


def _scrape(city_name: str, at: datetime) -> None:
    """Run the real Celery task for the city with the clock at `at`."""
    # The task closes stale connections; inside the test transaction that would
    # close the test's own connection.
    with (
        patch("django.utils.timezone.now", return_value=at),
        patch("pharmacies.tasks.close_old_connections"),
    ):
        run_scraper.apply(args=(city_name,), throw=True)


def _window(city_name: str, at: datetime) -> tuple[datetime, datetime]:
    with patch("django.utils.timezone.now", return_value=at):
        return get_duty_window(city_name)


def _field_values(field: str, upper: int) -> set[int]:
    if field == "*":
        return set(range(upper))
    return {int(part) for part in field.split(",")}


def _crontab_scrapes(city_name: str, first: datetime, last: datetime) -> list[datetime]:
    """Expand the city's enabled crontab scrape tasks into UTC datetimes."""
    tasks = PeriodicTask.objects.filter(
        enabled=True,
        task="pharmacies.tasks.run_scraper",
        args=json.dumps([city_name]),
        crontab__isnull=False,
    ).select_related("crontab")
    times: list[datetime] = []
    for task in tasks:
        cron = task.crontab
        assert cron is not None
        assert str(cron.timezone) == "UTC"
        minutes = _field_values(cron.minute, 60)
        hours = _field_values(cron.hour, 24)
        days = _field_values(cron.day_of_week, 7)
        day = first.replace(hour=0, minute=0)
        while day <= last:
            if (day.weekday() + 1) % 7 in days:  # celery: 0 = Sunday
                times.extend(
                    day.replace(hour=hour, minute=minute)
                    for hour in sorted(hours)
                    for minute in sorted(minutes)
                )
            day += timedelta(days=1)
    return [t for t in times if first <= t <= last]


def _hourly_scrapes(first: datetime, last: datetime) -> list[datetime]:
    """The interval scrape: production runs it at :55 of every hour."""
    times: list[datetime] = []
    at = first.replace(minute=55, second=0, microsecond=0)
    while at <= last:
        if at >= first:
            times.append(at)
        at += timedelta(hours=1)
    return times


def _covered(city: City, at: datetime) -> bool:
    if city.working_schedule.is_open(at):
        return True
    try:
        city.get_pharmacies_on_duty(at)
    except ValueError:
        return False
    return True


@pytest.mark.django_db
@pytest.mark.parametrize("city_name", CITIES)
@pytest.mark.parametrize("week", WEEKS)
def test_city_is_open_or_covered_at_every_step_of_the_week(
    city_name: str, week: str
) -> None:
    start = WEEKS[week]
    end = start + timedelta(days=7)
    city = _seed(city_name)
    first_scrape = start - WARM_UP
    scrapes = sorted(
        set(
            _crontab_scrapes(city_name, first_scrape, end)
            + _hourly_scrapes(first_scrape, end)
        )
    )

    uncovered: list[str] = []
    last_window: tuple[datetime, datetime] | None = None
    pending = iter(scrapes)
    upcoming = next(pending, None)
    step = start
    while step < end:
        # A scrape starting at the step has not finished at it: strictly before.
        while upcoming is not None and upcoming < step:
            # The recorded pages are the same on every scrape, so a scrape in the
            # same duty window as the last one rewrites the same rows (ADR 0005)
            # and is skipped; it keeps the sweep to seconds, not minutes.
            window = _window(city_name, upcoming)
            if window != last_window:
                _scrape(city_name, upcoming)
                last_window = window
            upcoming = next(pending, None)
        if not _covered(city, step):
            uncovered.append(step.strftime("%a %d %H:%M"))
        step += STEP

    assert uncovered == []


def _straight_line_distances(
    lat: float, lng: float, pharmacy_data: list[dict[str, Any]]
) -> None:
    """Stand in for Google's Distance Matrix: use the straight-line distance."""
    for item in pharmacy_data:
        item["travel_distance"] = item["distance"]
        item["travel_duration"] = item["distance"] / 1000 * 60


@pytest.fixture
def post_points(client: Client) -> Callable[[datetime], Any]:
    def post(at: datetime) -> Any:
        with (
            patch("django.utils.timezone.now", return_value=at),
            patch("pharmacies.views.get_city_name_from_location") as city_of,
            patch(
                "pharmacies.utils.utils.add_travel_distances_to_pharmacy_data",
                side_effect=_straight_line_distances,
            ),
        ):
            city_of.return_value = "ankara"
            return client.post(
                reverse("pharmacies:get_pharmacy_points"),
                data=json.dumps({"lat": 39.9334, "lng": 32.8597}),
                content_type="application/json",
            )

    return post


@pytest.mark.django_db
def test_ankara_has_duty_pharmacies_after_the_sunday_handover(
    post_points: Callable[[datetime], Any],
) -> None:
    assert settings.DEBUG is False
    _seed("ankara")
    saturday_night = datetime(2026, 11, 8, 5, 55, tzinfo=UTC)  # a Sunday
    handover = datetime(2026, 11, 8, 6, 0, tzinfo=UTC)
    _scrape("ankara", saturday_night)

    fired = [
        task
        for task in PeriodicTask.objects.filter(
            enabled=True,
            task="pharmacies.tasks.run_scraper",
            args=json.dumps(["ankara"]),
            crontab__isnull=False,
        ).select_related("crontab")
        if _fires_at(task, handover)
    ]
    assert fired, "no Ankara crontab task fires at Sunday 06:00 UTC"
    for task in fired:
        _scrape(json.loads(task.args)[0], handover)

    response = post_points(datetime(2026, 11, 8, 6, 15, tzinfo=UTC))

    assert response.status_code == 200, response.content
    assert response.json()["points"]


def _fires_at(task: PeriodicTask, at: datetime) -> bool:
    cron = task.crontab
    assert cron is not None
    return (
        at.minute in _field_values(cron.minute, 60)
        and at.hour in _field_values(cron.hour, 24)
        and (at.weekday() + 1) % 7 in _field_values(cron.day_of_week, 7)
    )
