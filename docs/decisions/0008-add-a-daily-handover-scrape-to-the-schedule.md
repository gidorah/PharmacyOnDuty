# Add a daily handover scrape to the schedule

## Status

Accepted, 8 Nov 2026 (#297). Replaces
[0007](0007-drive-scrape-schedules-from-the-database-and-remove-their-tasks.md),
whose decision it restates; only the number of crontab tasks changed.

## Context

The duty window rolls over at `HANDOVER` (06:00 UTC). On Sundays and holidays
cities stay closed all day, so the window rolls over at 06:00 and no opening
scrape follows. The last hourly scrape (at :55) fetched Saturday's window,
which ends at 06:00 on Sunday, and the next one ran at 06:55. For those 55
minutes nobody was on duty and the API answered 400 "No pharmacies are on duty
at this time." for Ankara (#297, related #298). Holidays such as 29 Oct 2026
behave the same.

## Decision

As 0007, with five crontab tasks instead of four. Each city gets:

- an interval task, written when a `ScraperConfig` is saved;
- four crontab tasks at the working-hour boundaries, written when a
  `WorkingSchedule` is saved;
- a fifth crontab task, `Scrape <city> Handover`, every day at 06:00 UTC
  (`HANDOVER`, `timezone="UTC"`), written by the same save.

Migration 0008 creates the handover task for every existing `WorkingSchedule`
(idempotent; its reverse removes them). Deleting a schedule or city and
renaming a city handle it like the other four.

## Alternatives

- Move the hourly phase to :00: changes the interval and its phase, which are
  out of scope, and the scrape would still race the rollover.
- Extend the outgoing window past 06:00: changes `get_duty_window`, out of
  scope.
- A task for Sundays and holidays only: crontab cannot express Turkish
  holidays.

## Consequences

- Everything in 0007's consequences still holds: the schedule is data and
  invisible to code review; `.save()` writes the tasks while bulk updates,
  `loaddata` and raw saves skip them; tasks link to the city by name only; the
  admin shows UTC times; a fresh database scrapes nothing until `seed_cities`.
- The handover task scrapes every day, one extra scrape a day per city. That
  includes Eskişehir, whose windows come from its source.
- Changing `HANDOVER` does not move existing tasks: re-save the schedules (or
  write a migration) to rewrite the crontab.
