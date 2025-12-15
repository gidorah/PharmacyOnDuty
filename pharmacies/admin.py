from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from pharmacies.models import City, Pharmacy, ScraperConfig, WorkingSchedule
from pharmacies.tasks import run_scraper


@admin.register(City)
class CityAdmin(admin.ModelAdmin[City]):
    list_display = ("name", "last_scraped_at")


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin[Pharmacy]):
    list_display = ("name", "location", "city", "phone", "email", "website")


@admin.register(WorkingSchedule)
class WorkingScheduleAdmin(admin.ModelAdmin[WorkingSchedule]):
    list_display = (
        "city",
        "weekday_start",
        "weekday_end",
        "saturday_start",
        "saturday_end",
    )


@admin.register(ScraperConfig)
class ScraperConfigAdmin(admin.ModelAdmin[ScraperConfig]):
    list_display = ("city", "interval", "last_run")
    readonly_fields = ("last_run",)
    actions = ["run_selected_scrapers"]

    @admin.action(description="Run selected scrapers now")
    def run_selected_scrapers(
        self, request: HttpRequest, queryset: QuerySet[ScraperConfig]
    ) -> None:
        for scraper in queryset:
            run_scraper.delay(scraper.city.name)
        self.message_user(request, f"Queued {queryset.count()} scrapers for execution")
