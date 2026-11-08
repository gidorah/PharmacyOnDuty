import importlib
import json

import pytest
from django.apps import apps
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from pharmacies.models import City, WorkingSchedule, schedule_task_name

migration = importlib.import_module("pharmacies.migrations.0008_handover_scrape_task")


def _pre_deploy_cities(*names: str) -> list[City]:
    """Cities with schedules but without the handover task, as before 0008."""
    from datetime import time

    cities = []
    for name in names:
        city = City.objects.create(name=name)
        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(5, 30),
            weekday_end=time(15, 30),
            saturday_start=time(7, 0),
            saturday_end=time(15, 0),
        )
        cities.append(city)
    PeriodicTask.objects.filter(name__endswith="Handover").delete()
    return cities


def _handover_tasks() -> list[PeriodicTask]:
    return list(PeriodicTask.objects.filter(name__endswith=" Handover"))


@pytest.mark.django_db
class TestHandoverMigration:
    def test_forward_creates_task_for_every_schedule(self) -> None:
        cities = _pre_deploy_cities("CityA", "CityB")
        assert _handover_tasks() == []

        migration.add_handover_tasks(apps, None)

        for city in cities:
            task = PeriodicTask.objects.get(
                name=schedule_task_name(city.name, "Handover")
            )
            assert task.task == "pharmacies.tasks.run_scraper"
            assert task.args == json.dumps([city.name])
            assert task.enabled is True
            assert task.crontab is not None
            assert task.crontab.minute == "0"
            assert task.crontab.hour == "6"
            assert task.crontab.day_of_week == "*"
            assert task.crontab.day_of_month == "*"
            assert task.crontab.month_of_year == "*"
            assert str(task.crontab.timezone) == "UTC"

    def test_forward_twice_creates_no_duplicates(self) -> None:
        _pre_deploy_cities("CityA", "CityB")

        migration.add_handover_tasks(apps, None)
        migration.add_handover_tasks(apps, None)

        assert len(_handover_tasks()) == 2
        assert (
            CrontabSchedule.objects.filter(
                minute="0", hour="6", day_of_week="*", timezone="UTC"
            ).count()
            == 1
        )

    def test_forward_on_database_that_already_has_the_task(self) -> None:
        city = City.objects.create(name="CityA")
        from datetime import time

        WorkingSchedule.objects.create(
            city=city,
            weekday_start=time(5, 30),
            weekday_end=time(15, 30),
            saturday_start=time(7, 0),
            saturday_end=time(15, 0),
        )
        assert len(_handover_tasks()) == 1

        migration.add_handover_tasks(apps, None)

        assert len(_handover_tasks()) == 1

    def test_reverse_removes_the_tasks_and_keeps_the_others(self) -> None:
        cities = _pre_deploy_cities("CityA", "CityB")
        migration.add_handover_tasks(apps, None)
        others = PeriodicTask.objects.exclude(name__endswith=" Handover").count()
        assert others == 8

        migration.remove_handover_tasks(apps, None)

        assert _handover_tasks() == []
        assert PeriodicTask.objects.exclude(name__endswith=" Handover").count() == 8
        assert [c.name for c in cities] == ["CityA", "CityB"]
