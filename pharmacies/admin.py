from django.contrib import admin

from pharmacies.models import City, Pharmacy, ScraperConfig, WorkingSchedule
from pharmacies.tasks import run_scraper


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


@admin.register(ScraperConfig)
class ScraperConfigAdmin(admin.ModelAdmin):
    list_display = ("city", "interval", "last_run")
    readonly_fields = ("last_run",)
    actions = ["run_selected_scrapers"]

    @admin.action(description="Run selected scrapers now")
    def run_selected_scrapers(self, request, queryset):
        for scraper in queryset:
            run_scraper.delay(scraper.city.name)
        self.message_user(request, f"Queued {queryset.count()} scrapers for execution")
