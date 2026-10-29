# Drive scrape schedules from the database, and remove their tasks with them

## Status

Accepted, 29 Oct 2026 (#252). Replaces
[0002](0002-drive-scrape-schedules-from-the-database.md), whose decision it
restates; only the consequences about removing tasks changed.

## Context

Duty shifts start and end when ordinary pharmacies close and open, which is
also when the city status flips between open and closed. The duty list must
be fresh at those moments, not only once an hour. That the schedule should be
changeable without a deploy is inferred, not recorded.

Under 0002 nothing removed a city's beat tasks, so deleting a schedule, a
config or a city, or renaming a city, left tasks that kept scraping (#252).

## Decision

Beat uses `django_celery_beat`'s `DatabaseScheduler`. Each city gets two kinds
of scrape task, both calling `pharmacies.tasks.run_scraper` with the city
name:

- an interval task, written when a `ScraperConfig` is saved (model default
  24 hours; `seed_cities` sets 1 hour);
- four crontab tasks at the working-hour boundaries (weekday and Saturday,
  start and end), written when a `WorkingSchedule` is saved.

The tasks go with the rows that wrote them: `pre_delete` receivers remove a
`WorkingSchedule`'s four tasks and a `ScraperConfig`'s interval task, and
`City.save()` replaces a city's tasks when its name changes.

`WorkingSchedule` times are stored in UTC and the crontabs are created with
`timezone="UTC"`, although `TIME_ZONE` and `CELERY_TIMEZONE` are
`Europe/Istanbul`. `is_open` compares them with `timezone.now()` (UTC).

## Alternatives

- A static `CELERY_BEAT_SCHEDULE` in settings: reviewed in code and
  reproducible from the repo, but a schedule change needs a deploy.
- Interval only: duty lists could be up to an hour stale when the city closes.
- `delete()` overrides instead of receivers: the admin's bulk delete and the
  `City` cascade never call a child's `delete()`.
- A foreign key from `PeriodicTask` to `City`: `PeriodicTask` belongs to
  `django_celery_beat`, so it would need a link table and a migration.

## Consequences

- The schedule is data: code review never sees it, and the repo alone cannot
  reproduce it.
- `.save()` on these models writes beat tasks. Bulk updates, `loaddata` and
  raw saves skip that, and a `QuerySet.update()` of a city's name leaves its
  tasks under the old name.
- The tasks link to the city by name only (task name and `args`). The
  receivers find them by the names the models write; a task renamed by hand
  in the admin is not removed.
- Tasks left behind before this record (deleted or renamed cities) are not
  cleaned up; check `django_celery_beat_periodictask` by hand.
- Their `CrontabSchedule` and `IntervalSchedule` rows stay, since other tasks
  share them.
- The admin shows and takes these times in UTC. 08:30 in Turkey is 05:30.
  Do not "fix" the times to local without changing `is_open` and the crontabs
  together.
- A fresh database scrapes nothing until `seed_cities` runs. The testenv runs
  it at start, so beat there may scrape the live sites.
