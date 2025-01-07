from django.contrib.gis.db import models
from enum import StrEnum
from datetime import datetime


class PharmacyStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    ON_DUTY = "on_duty"


class City(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)

    def get_city_status(self):
        return self.working_schedule.get_current_status()

    def get_pharmacies_on_duty(self):
        return self.pharmacies.filter(
            duty_start__lte=datetime.now(),
            duty_end__gte=datetime.now(),
        )


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

    def get_current_status(self):
        current_time = datetime.now().time()
        current_weekday = datetime.now().weekday()

        def is_weekday_open():
            return (
                current_weekday < 5
                and self.weekday_start < current_time < self.weekday_end
            )

        def is_saturday_open():
            return (
                current_weekday == 5
                and self.saturday_start < current_time < self.saturday_end
            )

        if is_weekday_open() or is_saturday_open():
            return PharmacyStatus.OPEN

        return PharmacyStatus.CLOSED

    def __str__(self):
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

    def __str__(self):
        return self.name
