from django.contrib import admin

from pharmacies.models import City, Pharmacy, WorkingSchedule


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "last_scraped_at")


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "city", "phone", "email", "website")


@admin.register(WorkingSchedule)
class WorkingScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "city",
        "weekday_start",
        "weekday_end",
        "saturday_start",
        "saturday_end",
    )
