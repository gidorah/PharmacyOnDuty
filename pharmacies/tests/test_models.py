from datetime import UTC, datetime, time

import pytest
from django.contrib.gis.geos import Point

from pharmacies.models import City, Pharmacy, PharmacyStatus, WorkingSchedule


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
