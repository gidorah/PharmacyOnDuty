import json
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Optional

from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class PharmacyStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ON_DUTY = "on_duty"


class City(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    last_scraped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def get_pharmacies_on_duty(self, current_time: datetime | None = None) -> list[Any]:
        """Return pharmacies that are on duty at the given time."""
        current_time = current_time or timezone.now()
        pharmacies_on_duty = list(
            self.pharmacies.filter(
                duty_start__lte=current_time, duty_end__gte=current_time
            )
        )
        if not pharmacies_on_duty:
            raise ValueError("No pharmacies are on duty at this time.")
        return pharmacies_on_duty

    def get_city_status(self, query_time: datetime | None = None) -> PharmacyStatus:
        """Return the city status for the given time."""
        query_time = query_time or timezone.now()
        status = self.working_schedule.get_status(query_time=query_time)
        if not status:
            raise ValueError("Unable to retrieve city status.")
        return status

    def __str__(self) -> str:
        return self.name


class WorkingSchedule(models.Model):
    city = models.OneToOneField(
        City,
        on_delete=models.CASCADE,
        related_name="working_schedule",
        null=False,
        blank=False,
    )
    weekday_start = models.TimeField(null=False, blank=False)
    weekday_end = models.TimeField(null=False, blank=False)
    saturday_start = models.TimeField(null=False, blank=False)
    saturday_end = models.TimeField(null=False, blank=False)

    class Meta:
        verbose_name = "Working Schedule"
        verbose_name_plural = "Working Schedules"

    def is_open(self, query_time: datetime) -> bool:
        """Check if the working schedule is open at the given time."""
        current_time = query_time.time()
        current_weekday = query_time.weekday()
        return (
            current_weekday < 5 and self.weekday_start < current_time < self.weekday_end
        ) or (
            current_weekday == 5
            and self.saturday_start < current_time < self.saturday_end
        )

    def get_status(self, query_time: Optional[datetime] = None) -> PharmacyStatus:
        """Return the status of the working schedule for the given time."""
        return (
            PharmacyStatus.OPEN
            if self.is_open(query_time or timezone.now())
            else PharmacyStatus.CLOSED
        )

    def __str__(self) -> str:
        return f"Schedule for {self.city.name}"


class Pharmacy(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    location = models.PointField(null=False, blank=False, default="POINT(0 0)")
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="pharmacies",
        null=False,
        blank=False,
    )
    district = models.CharField(max_length=100, null=False, blank=False)
    phone = models.CharField(max_length=16, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    duty_start = models.DateTimeField(null=True, blank=True)
    duty_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Pharmacy"
        verbose_name_plural = "Pharmacies"

        indexes = [
            # Spatial Index for location (critical for distance queries)
            GistIndex(fields=["location"]),
            # Indexes for time-based filtering
            models.Index(fields=["duty_start"]),
            models.Index(fields=["duty_end"]),
        ]

    def __str__(self) -> str:
        return self.name


class ScraperConfig(models.Model):
    city = models.OneToOneField(City, on_delete=models.CASCADE, primary_key=True)
    interval = models.PositiveIntegerField(
        default=24, help_text="Update interval in hours"
    )
    last_run = models.DateTimeField(null=True, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)
        self._update_celery_schedule()

    def _update_celery_schedule(self) -> None:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=self.interval, period=IntervalSchedule.HOURS
        )

        PeriodicTask.objects.update_or_create(
            name=f"Scrape {self.city.name} ({self.id})",  # Unique name
            defaults={
                "interval": schedule,
                "task": "pharmacies.tasks.run_scraper",
                "args": json.dumps([self.city.name]),
                "enabled": True,
                "expires": timezone.now() + timedelta(hours=1),
            },
        )
