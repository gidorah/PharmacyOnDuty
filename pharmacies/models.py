"""
Database models for the Pharmacies application.

This module defines the data structure for Cities, Pharmacies, Working Schedules,
and Scraper Configurations, including their relationships and logic.
"""

import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex
from django.utils import timezone
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask


class PharmacyStatus(StrEnum):
    """
    Enum representing the operational status of a pharmacy or city.

    Attributes:
        OPEN: The entity is currently open for business.
        CLOSED: The entity is currently closed.
        ON_DUTY: The pharmacy is currently serving as a duty pharmacy.
    """

    OPEN = "open"
    CLOSED = "closed"
    ON_DUTY = "on_duty"


class City(models.Model):
    """
    Model representing a city that contains pharmacies.

    Attributes:
        name: The name of the city.
        last_scraped_at: Timestamp of the last successful scraper run for this city.
    """

    name = models.CharField(max_length=100, null=False, blank=False)
    last_scraped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta options for City model."""

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
        return str(self.name)


class WorkingSchedule(models.Model):
    """
    Model defining the standard working hours for pharmacies in a specific city.

    This schedule determines when pharmacies are considered 'OPEN' versus 'CLOSED'
    (excluding duty shifts).

    Attributes:
        city: The city this schedule applies to.
        weekday_start: Opening time on weekdays (Mon-Fri).
        weekday_end: Closing time on weekdays (Mon-Fri).
        saturday_start: Opening time on Saturdays.
        saturday_end: Closing time on Saturdays.
    """

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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the schedule and update associated periodic tasks.

        This overrides the default save method to ensure that Celery periodic tasks
        are created or updated whenever the working schedule changes.
        """
        super().save(*args, **kwargs)
        self._update_periodic_tasks()

    def _update_periodic_tasks(self) -> None:
        """
        Create or update Celery PeriodicTasks based on the schedule.

        This method generates four periodic tasks for the city:
        1. Weekday Start
        2. Weekday End
        3. Saturday Start
        4. Saturday End
        """

        # Helper to create/get crontab and task
        def create_task(suffix: str, hour: int, minute: int, days: str) -> None:
            """Helper to create or update a Celery periodic task."""
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week=days,
                day_of_month="*",
                month_of_year="*",
                timezone="UTC",  # Assuming time fields are in UTC
            )

            PeriodicTask.objects.update_or_create(
                name=f"Scrape {self.city.name} {suffix}",
                defaults={
                    "crontab": schedule,
                    "task": "pharmacies.tasks.run_scraper",
                    "args": json.dumps([self.city.name]),
                    "enabled": True,
                },
            )

        # 1. Weekday Start (Mon-Fri)
        create_task(
            "Weekday Start",
            self.weekday_start.hour,
            self.weekday_start.minute,
            "1,2,3,4,5",
        )
        # 2. Weekday End (Mon-Fri)
        create_task(
            "Weekday End", self.weekday_end.hour, self.weekday_end.minute, "1,2,3,4,5"
        )
        # 3. Saturday Start (Sat)
        create_task(
            "Saturday Start",
            self.saturday_start.hour,
            self.saturday_start.minute,
            "6",
        )
        # 4. Saturday End (Sat)
        create_task(
            "Saturday End", self.saturday_end.hour, self.saturday_end.minute, "6"
        )

    class Meta:
        """Meta options for WorkingSchedule model."""

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

    def get_status(self, query_time: datetime | None = None) -> PharmacyStatus:
        """Return the status of the working schedule for the given time."""
        return (
            PharmacyStatus.OPEN
            if self.is_open(query_time or timezone.now())
            else PharmacyStatus.CLOSED
        )

    def __str__(self) -> str:
        return f"Schedule for {self.city.name}"


class Pharmacy(models.Model):
    """
    Model representing a specific pharmacy.

    Attributes:
        name: Name of the pharmacy.
        location: Geospatial point (latitude/longitude) of the pharmacy.
        address: Physical address.
        city: The city the pharmacy belongs to.
        district: The district within the city.
        phone: Contact phone number.
        email: Contact email address.
        website: URL of the pharmacy's website.
        duty_start: Start datetime of the current or next duty shift.
        duty_end: End datetime of the current or next duty shift.
    """

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
        """Meta options for Pharmacy model."""

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
        return str(self.name)


class ScraperConfig(models.Model):
    """
    Configuration for the city-specific scraper.

    Attributes:
        city: The city this configuration applies to.
        interval: The frequency (in hours) at which the scraper should run.
        last_run: Timestamp of the last execution.
    """

    city = models.OneToOneField(City, on_delete=models.CASCADE, primary_key=True)
    interval = models.PositiveIntegerField(
        default=24, help_text="Update interval in hours"
    )
    last_run = models.DateTimeField(null=True, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Save the config and update the Celery schedule.

        Overrides default save to ensure the associated Celery PeriodicTask
        is updated with the new interval.
        """
        super().save(*args, **kwargs)
        self._update_celery_schedule()

    def _update_celery_schedule(self) -> None:
        """Create or update the Celery IntervalSchedule and PeriodicTask."""
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=self.interval, period=IntervalSchedule.HOURS
        )

        PeriodicTask.objects.update_or_create(
            name=f"Scrape {self.city.name} ({self.pk})",  # Unique name
            defaults={
                "interval": schedule,
                "task": "pharmacies.tasks.run_scraper",
                "args": json.dumps([self.city.name]),
                "enabled": True,
            },
        )
