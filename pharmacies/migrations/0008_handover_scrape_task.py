import json

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

TASK_SUFFIX = "Handover"
HANDOVER_HOUR = 6  # UTC, HANDOVER in pharmacies.models; frozen here
HANDOVER_MINUTE = 0


def add_handover_tasks(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Write the daily handover task for every existing WorkingSchedule."""
    crontab_model = apps.get_model("django_celery_beat", "CrontabSchedule")
    task_model = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule_model = apps.get_model("pharmacies", "WorkingSchedule")

    crontab = None
    for schedule in schedule_model.objects.select_related("city"):
        if crontab is None:
            crontab, _ = crontab_model.objects.get_or_create(
                minute=str(HANDOVER_MINUTE),
                hour=str(HANDOVER_HOUR),
                day_of_week="*",
                day_of_month="*",
                month_of_year="*",
                timezone="UTC",
            )
        task_model.objects.update_or_create(
            name=f"Scrape {schedule.city.name} {TASK_SUFFIX}",
            defaults={
                "crontab": crontab,
                "task": "pharmacies.tasks.run_scraper",
                "args": json.dumps([schedule.city.name]),
                "enabled": True,
            },
        )


def remove_handover_tasks(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Remove the handover task of every existing WorkingSchedule."""
    task_model = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule_model = apps.get_model("pharmacies", "WorkingSchedule")
    names = [
        f"Scrape {schedule.city.name} {TASK_SUFFIX}"
        for schedule in schedule_model.objects.select_related("city")
    ]
    task_model.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacies", "0007_scraperconfig"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [migrations.RunPython(add_handover_tasks, remove_handover_tasks)]
