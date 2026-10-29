import json
from datetime import UTC, datetime, time

import pytest
from django.contrib.gis.geos import Point
from django_celery_beat.models import PeriodicTask

from pharmacies.models import (
    City,
    Pharmacy,
    PharmacyStatus,
    ScraperConfig,
    WorkingSchedule,
)


def _create_realistic_schedule(
    city: City, weekday_end: time = time(15, 0)
) -> WorkingSchedule:
    return WorkingSchedule.objects.create(
        city=city,
        weekday_start=time(6, 0),
        weekday_end=weekday_end,
        saturday_start=time(6, 0),
        saturday_end=time(11, 0),
    )


@pytest.mark.django_db
class TestCityModel:
    def test_city_creation(self) -> None:
        city = City.objects.create(name="Eskişehir")
        assert str(city) == "Eskişehir"
        assert city.name == "Eskişehir"

    def test_get_city_status_open(self) -> None:
        city = City.objects.create(name="Eskişehir")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Tuesday at 10:00
        query_time = datetime(2025, 12, 16, 10, 0, tzinfo=UTC)
        assert city.get_city_status(query_time) == PharmacyStatus.OPEN

    def test_get_city_status_closed(self) -> None:
        city = City.objects.create(name="Eskişehir")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Tuesday at 20:00
        query_time = datetime(2025, 12, 16, 20, 0, tzinfo=UTC)
        assert city.get_city_status(query_time) == PharmacyStatus.CLOSED

    def test_get_city_status_closed_on_public_holiday(self) -> None:
        city = City.objects.create(name="Eskişehir")
        _create_realistic_schedule(city)

        # Republic Day (Thursday), inside the usual weekday hours
        query_time = datetime(2026, 10, 29, 7, 0, tzinfo=UTC)
        assert city.get_city_status(query_time) == PharmacyStatus.CLOSED

    def test_get_pharmacies_on_duty_success(self) -> None:
        city = City.objects.create(name="Eskişehir")
        pharmacy = Pharmacy.objects.create(
            name="Test Pharmacy",
            city=city,
            district="Odunpazarı",
            location=Point(30.5, 39.7),
            duty_start=datetime(2025, 12, 16, 18, 0, tzinfo=UTC),
            duty_end=datetime(2025, 12, 17, 8, 0, tzinfo=UTC),
        )

        query_time = datetime(2025, 12, 16, 22, 0, tzinfo=UTC)
        on_duty = city.get_pharmacies_on_duty(query_time)
        assert len(on_duty) == 1
        assert on_duty[0] == pharmacy

    def test_get_pharmacies_on_duty_empty(self) -> None:
        city = City.objects.create(name="Eskişehir")
        query_time = datetime(2025, 12, 16, 22, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="No pharmacies are on duty at this time."):
            city.get_pharmacies_on_duty(query_time)


@pytest.mark.django_db
class TestWorkingScheduleModel:
    def test_is_open_weekday(self) -> None:
        city = City.objects.create(name="Test City")
        schedule = WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Monday 10:00 - Open
        assert schedule.is_open(datetime(2025, 12, 15, 10, 0)) is True
        # Monday 08:00 - Closed
        assert schedule.is_open(datetime(2025, 12, 15, 8, 0)) is False
        # Monday 19:00 - Closed
        assert schedule.is_open(datetime(2025, 12, 15, 19, 0)) is False

    def test_is_open_saturday(self) -> None:
        city = City.objects.create(name="Test City")
        schedule = WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Saturday 10:00 - Open
        assert schedule.is_open(datetime(2025, 12, 20, 10, 0)) is True
        # Saturday 14:00 - Closed
        assert schedule.is_open(datetime(2025, 12, 20, 14, 0)) is False

    def test_is_open_sunday(self) -> None:
        city = City.objects.create(name="Test City")
        schedule = WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(9, 0),
            weekday_end=time(18, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )

        # Sunday - Always closed
        assert schedule.is_open(datetime(2025, 12, 21, 10, 0)) is False

    def test_is_closed_on_weekday_public_holiday(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        assert schedule.is_open(datetime(2026, 10, 29, 7, 0, tzinfo=UTC)) is False

    def test_is_closed_on_saturday_public_holiday(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        # Kurban Bayrami 2026-05-30 is a Saturday
        assert schedule.is_open(datetime(2026, 5, 30, 8, 0, tzinfo=UTC)) is False

    def test_is_closed_on_2027_bayram(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        # Ramazan Bayrami day 1, Tuesday
        assert schedule.is_open(datetime(2027, 3, 9, 8, 0, tzinfo=UTC)) is False

    def test_naive_query_time_is_treated_as_utc(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        assert schedule.is_open(datetime(2026, 10, 29, 7, 0)) is False
        assert schedule.is_open(datetime(2026, 10, 28, 9, 0)) is True

    def test_eve_open_until_1300_istanbul(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        # 2026-10-28 is the eve of Republic Day (Wednesday)
        assert schedule.is_open(datetime(2026, 10, 28, 9, 0, tzinfo=UTC)) is True
        assert schedule.is_open(datetime(2026, 10, 28, 10, 30, tzinfo=UTC)) is False

    def test_eve_closed_before_usual_start(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        assert schedule.is_open(datetime(2026, 10, 28, 5, 0, tzinfo=UTC)) is False

    def test_eve_on_saturday_uses_saturday_hours(self) -> None:
        schedule = WorkingSchedule.objects.create(
            city=City.objects.create(name="Test City"),
            weekday_start=time(6, 0),
            weekday_end=time(15, 0),
            saturday_start=time(6, 0),
            saturday_end=time(12, 0),
        )
        # 2027-05-15 is a Saturday eve
        assert schedule.is_open(datetime(2027, 5, 15, 9, 0, tzinfo=UTC)) is True
        assert schedule.is_open(datetime(2027, 5, 15, 10, 30, tzinfo=UTC)) is False

    def test_eve_closes_at_usual_end_when_earlier(self) -> None:
        schedule = _create_realistic_schedule(
            City.objects.create(name="Test City"), weekday_end=time(9, 0)
        )
        assert schedule.is_open(datetime(2026, 10, 28, 8, 30, tzinfo=UTC)) is True
        assert schedule.is_open(datetime(2026, 10, 28, 9, 30, tzinfo=UTC)) is False

    def test_istanbul_date_after_utc_midnight_eve_is_holiday(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        # 22:30 UTC on 28 Oct is 01:30 on 29 Oct in Istanbul
        assert schedule.is_open(datetime(2026, 10, 28, 22, 30, tzinfo=UTC)) is False

    def test_istanbul_date_after_utc_midnight_ordinary_day(self) -> None:
        schedule = WorkingSchedule.objects.create(
            city=City.objects.create(name="Test City"),
            weekday_start=time(21, 0),
            weekday_end=time(23, 0),
            saturday_start=time(9, 0),
            saturday_end=time(13, 0),
        )
        # 21:30 UTC on Thursday 29 Oct is 00:30 Friday 30 Oct in Istanbul: ordinary
        assert schedule.is_open(datetime(2026, 10, 29, 21, 30, tzinfo=UTC)) is True
        # Same hour, ordinary Thursday a week later behaves identically
        assert schedule.is_open(datetime(2026, 11, 5, 21, 30, tzinfo=UTC)) is True

    def test_sunday_eve_stays_closed(self) -> None:
        schedule = _create_realistic_schedule(City.objects.create(name="Test City"))
        # Ordinary Sunday inside the weekday hours
        assert schedule.is_open(datetime(2026, 11, 1, 8, 0, tzinfo=UTC)) is False

    def test_update_periodic_tasks(self) -> None:
        from django_celery_beat.models import PeriodicTask

        city = City.objects.create(name="TaskCity")
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(8, 30),
            weekday_end=time(18, 30),
            saturday_start=time(8, 30),
            saturday_end=time(13, 30),
        )

        tasks = PeriodicTask.objects.filter(name__icontains="Scrape TaskCity")
        assert tasks.count() == 4
        assert tasks.filter(name__icontains="Weekday Start").exists()
        assert tasks.filter(name__icontains="Weekday End").exists()
        assert tasks.filter(name__icontains="Saturday Start").exists()
        assert tasks.filter(name__icontains="Saturday End").exists()


@pytest.mark.django_db
class TestPharmacyModel:
    def test_pharmacy_creation(self) -> None:
        city = City.objects.create(name="Eskişehir")
        pharmacy = Pharmacy.objects.create(
            name="Test Pharmacy",
            city=city,
            district="Odunpazarı",
            location=Point(30.5, 39.7),
        )
        assert str(pharmacy) == "Test Pharmacy"
        assert pharmacy.city == city

    def test_spatial_query(self) -> None:
        city = City.objects.create(name="Eskişehir")
        p1 = Pharmacy.objects.create(
            name="Near", city=city, district="D1", location=Point(30.0, 39.0)
        )
        p2 = Pharmacy.objects.create(
            name="Far", city=city, district="D1", location=Point(31.0, 40.0)
        )

        # Query for pharmacies near (30.01, 39.01)
        from django.contrib.gis.db.models.functions import Distance

        ref_location = Point(30.01, 39.01, srid=4326)
        near_pharmacies = Pharmacy.objects.annotate(
            distance=Distance("location", ref_location)
        ).order_by("distance")

        assert near_pharmacies[0] == p1
        assert near_pharmacies[1] == p2


SCRAPER_TASK = "pharmacies.tasks.run_scraper"


def _names_for(city: City) -> set[str]:
    """Expected five task names for a city."""
    return {
        f"Scrape {city.name} Weekday Start",
        f"Scrape {city.name} Weekday End",
        f"Scrape {city.name} Saturday Start",
        f"Scrape {city.name} Saturday End",
        f"Scrape {city.name} ({city.pk})",
    }


def _task_names() -> set[str]:
    return set(
        PeriodicTask.objects.filter(task=SCRAPER_TASK).values_list("name", flat=True)
    )


def _make_city(name: str) -> City:
    city = City.objects.create(name=name)
    WorkingSchedule.objects.create(
        city=city,
        weekday_start=time(9, 0),
        weekday_end=time(18, 0),
        saturday_start=time(9, 0),
        saturday_end=time(13, 0),
    )
    ScraperConfig.objects.create(city=city, interval=12)
    return city


@pytest.mark.django_db
class TestPeriodicTaskCleanup:
    def test_deleting_schedule_removes_its_four_tasks(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        city_a.working_schedule.delete()
        assert _task_names() == {f"Scrape CityA ({city_a.pk})"} | _names_for(city_b)

    def test_deleting_config_removes_its_interval_task(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        city_a.scraperconfig.delete()
        assert _task_names() == (
            _names_for(city_a) - {f"Scrape CityA ({city_a.pk})"}
        ) | _names_for(city_b)

    def test_deleting_city_removes_all_its_tasks(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        city_a.delete()
        assert _task_names() == _names_for(city_b)
        assert not PeriodicTask.objects.filter(args=json.dumps(["CityA"])).exists()

    def test_queryset_delete_of_schedules(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        WorkingSchedule.objects.filter(city=city_a).delete()
        assert _task_names() == {f"Scrape CityA ({city_a.pk})"} | _names_for(city_b)

    def test_queryset_delete_of_configs(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        ScraperConfig.objects.filter(city=city_a).delete()
        assert _task_names() == (
            _names_for(city_a) - {f"Scrape CityA ({city_a.pk})"}
        ) | _names_for(city_b)

    def test_queryset_delete_of_cities(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        City.objects.filter(pk=city_a.pk).delete()
        assert _task_names() == _names_for(city_b)
        assert not PeriodicTask.objects.filter(args=json.dumps(["CityA"])).exists()


@pytest.mark.django_db
class TestCityRenameTasks:
    def test_rename_moves_tasks_to_new_name(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        city = City.objects.get(pk=city_a.pk)
        city.name = "CityC"
        city.save()
        assert _task_names() == _names_for(city) | _names_for(city_b)
        for name in _names_for(city):
            task = PeriodicTask.objects.get(name=name)
            assert task.args == json.dumps(["CityC"])
        assert not PeriodicTask.objects.filter(args=json.dumps(["CityA"])).exists()

    def test_rename_city_without_schedule_or_config_creates_no_tasks(self) -> None:
        city = City.objects.create(name="Bare")
        city.name = "Bare2"
        city.save()
        assert _task_names() == set()

    def test_save_without_rename_keeps_tasks(self) -> None:
        city_a, city_b = _make_city("CityA"), _make_city("CityB")
        city = City.objects.get(pk=city_a.pk)
        city.save()
        assert _task_names() == _names_for(city_a) | _names_for(city_b)
