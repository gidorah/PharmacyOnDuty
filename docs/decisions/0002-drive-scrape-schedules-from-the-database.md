# Drive scrape schedules from the database, at working-hour boundaries

## Status

Replaced by [0007](0007-drive-scrape-schedules-from-the-database-and-remove-their-tasks.md).
Back-filled 28 Oct 2026 from commit 3060c4b (18 Dec 2025,
"dual-strategy scraper scheduling").

## Context

Duty shifts start and end when ordinary pharmacies close and open, which is
also when the city status flips between open and closed. The duty list must
be fresh at those moments, not only once an hour. That the schedule should be
changeable without a deploy is inferred, not recorded.

## Decision

Beat uses `django_celery_beat`'s `DatabaseScheduler`. Each city gets two kinds
of scrape task, both calling `pharmacies.tasks.run_scraper` with the city
name:

- an interval task, written when a `ScraperConfig` is saved (model default
  24 hours; `seed_cities` sets 1 hour);
- four crontab tasks at the working-hour boundaries (weekday and Saturday,
  start and end), written when a `WorkingSchedule` is saved.

`WorkingSchedule` times are stored in UTC and the crontabs are created with
`timezone="UTC"`, although `TIME_ZONE` and `CELERY_TIMEZONE` are
`Europe/Istanbul`. `is_open` compares them with `timezone.now()` (UTC).

## Alternatives

- A static `CELERY_BEAT_SCHEDULE` in settings: reviewed in code and
  reproducible from the repo, but a schedule change needs a deploy.
- Interval only: duty lists could be up to an hour stale when the city closes.

## Consequences

- The schedule is data: code review never sees it, and the repo alone cannot
  reproduce it.
- `.save()` on these models writes beat tasks. Bulk updates, `loaddata` and
  raw saves skip that.
- Neither model removes its tasks. Deleting a schedule or config, or renaming
  a city (task names contain it), leaves tasks that keep scraping.
- The admin shows and takes these times in UTC. 08:30 in Turkey is 05:30.
  Do not "fix" the times to local without changing `is_open` and the crontabs
  together.
- A fresh database scrapes nothing until `seed_cities` runs. The testenv runs
  it at start, so beat there may scrape the live sites.
