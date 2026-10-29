"""Duty window shared by the scrapers that don't read it from their source."""

from datetime import UTC, datetime, time, timedelta

from django.utils import timezone

from pharmacies.models import WorkingSchedule

HANDOVER = time(6, 0)  # UTC; the day rolls over here, or at the opening if later


def _at(day: datetime, at: time) -> datetime:
    return datetime.combine(day.date(), at, tzinfo=UTC)


def _opening(schedule: WorkingSchedule, weekday: int) -> time:
    if weekday == 5:
        return schedule.saturday_start
    if weekday == 6:
        return HANDOVER
    return schedule.weekday_start


def get_duty_window(city_name: str) -> tuple[datetime, datetime]:
    """
    Compute the current duty window of a city from the time and its schedule.

    All times are UTC, like the `WorkingSchedule`. The day rolls over at the
    later of 06:00 and that day's opening (Saturday: `saturday_start`; weekdays:
    `weekday_start`; Sunday: 06:00): before it, the window is the one that
    started the previous day. So a scrape never replaces a window that is still
    needed while the city is closed.

    - Mon-Thu: from `weekday_end` to the later of 06:00 the next day and the
      next day's `weekday_start`.
    - Friday: from `weekday_end` to the later of 06:00 Saturday and
      `saturday_start`.
    - Saturday: from `saturday_end` to 06:00 Sunday.
    - Sunday: from 06:00 Sunday to 06:00 Monday.

    The window starts when the city closes, so no time between closing and the
    window is left uncovered.
    """
    schedule = WorkingSchedule.objects.get(city__name=city_name)
    now = timezone.now().astimezone(UTC)
    day = now
    if now.time() < max(HANDOVER, _opening(schedule, now.weekday())):
        day -= timedelta(days=1)

    handover = _at(day + timedelta(days=1), HANDOVER)
    weekday = day.weekday()
    if weekday == 6:
        return _at(day, HANDOVER), handover
    if weekday == 5:
        return _at(day, schedule.saturday_end), handover

    next_opening = _at(
        day + timedelta(days=1),
        schedule.saturday_start if weekday == 4 else schedule.weekday_start,
    )
    return _at(day, schedule.weekday_end), max(handover, next_opening)
