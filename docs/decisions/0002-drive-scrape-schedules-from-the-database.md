# Drive scrape schedules from the database

## Status

Accepted. Back-filled 28 Oct 2026.

## Context

Duty lists change at fixed times of day, and each city's chamber publishes on
its own schedule. Changing a schedule should not need a deploy.

## Decision

Beat uses `django_celery_beat`'s `DatabaseScheduler`. Saving a
`WorkingSchedule` creates or updates four `PeriodicTask` rows for the city
(weekday and Saturday, start and end), and saving a `ScraperConfig` creates or
updates one interval task. Both call `pharmacies.tasks.run_scraper` with the
city name. `manage.py seed_cities` creates the three cities with an hourly
interval.

## Consequences

- The schedule is data: the admin site or a shell changes it, and code review
  never sees it.
- `.save()` on these models has a side effect on beat. Bulk updates skip it.
- `WorkingSchedule` times are stored in UTC (`seed_cities` converts from
  Turkey time); the crontabs are created with `timezone="UTC"`.
- A fresh database scrapes nothing until `seed_cities` runs; the testenv runs
  it at start, so beat there may scrape the live sites.
