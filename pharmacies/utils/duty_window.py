"""Duty window shared by the scrapers that don't read it from their source."""

from datetime import UTC, date, datetime, time, timedelta

from django.utils import timezone

from pharmacies.models import (
    EVE_CLOSING_TIME_ISTANBUL,
    ISTANBUL_TZ,
    TR_HALF_DAY_HOLIDAYS,
    TR_PUBLIC_HOLIDAYS,
    WorkingSchedule,
)

HANDOVER = time(6, 0)  # UTC; the day rolls over here, or at the opening if later


def _at(day: datetime, at: time) -> datetime:
    return datetime.combine(day.date(), at, tzinfo=UTC)


def _istanbul_date(day: datetime) -> date:
    """The Istanbul date of the day's handover, the date holidays are listed by."""
    return _at(day, HANDOVER).astimezone(ISTANBUL_TZ).date()


def _is_holiday(day: datetime) -> bool:
    return _istanbul_date(day) in TR_PUBLIC_HOLIDAYS


def _opening(schedule: WorkingSchedule, day: datetime) -> time:
    if _is_holiday(day) or day.weekday() == 6:
        return HANDOVER
    if day.weekday() == 5:
        return schedule.saturday_start
    return schedule.weekday_start


def _closing(schedule: WorkingSchedule, day: datetime) -> time:
    """When the city closes on a working day, as `WorkingSchedule.is_open` does."""
    end = schedule.saturday_end if day.weekday() == 5 else schedule.weekday_end
    istanbul_date = _istanbul_date(day)
    if istanbul_date in TR_HALF_DAY_HOLIDAYS:
        eve_close = (
            datetime.combine(istanbul_date, EVE_CLOSING_TIME_ISTANBUL, ISTANBUL_TZ)
            .astimezone(UTC)
            .time()
        )
        return min(end, eve_close)
    return end


def get_duty_window(city_name: str) -> tuple[datetime, datetime]:
    """
    Compute the current duty window of a city from the time and its schedule.

    All times are UTC, like the `WorkingSchedule`. The day rolls over at the
    later of 06:00 and that day's opening (Saturday: `saturday_start`; weekdays:
    `weekday_start`; Sunday and Turkish public holidays: 06:00): before it, the
    window is the one that started the previous day. So a scrape never replaces
    a window that is still needed while the city is closed.

    - Mon-Thu: from the closing to the later of 06:00 the next day and the
      next day's opening.
    - Friday: from the closing to the later of 06:00 Saturday and
      `saturday_start`.
    - Saturday: from the closing to 06:00 Sunday.
    - Sunday: from 06:00 Sunday to 06:00 Monday.
    - Public holiday (`TR_PUBLIC_HOLIDAYS`, by Istanbul date): like a Sunday,
      from 06:00 that day to the later of 06:00 the next day and the next
      day's opening.
    - A working day followed by a holiday ends at 06:00, since the holiday
      opens at 06:00.

    The closing is `weekday_end` or `saturday_end`, or on a half-day eve
    (`TR_HALF_DAY_HOLIDAYS`) the earlier of that and 13:00 Europe/Istanbul,
    like `WorkingSchedule.is_open`. The window starts when the city closes, so
    no time between closing and the window is left uncovered.
    """
    schedule = WorkingSchedule.objects.get(city__name=city_name)
    now = timezone.now().astimezone(UTC)
    day = now
    if now.time() < max(HANDOVER, _opening(schedule, now)):
        day -= timedelta(days=1)

    next_day = day + timedelta(days=1)
    handover = _at(next_day, HANDOVER)
    if day.weekday() == 6:
        return _at(day, HANDOVER), handover

    next_opening = _at(next_day, _opening(schedule, next_day))
    if _is_holiday(day):
        return _at(day, HANDOVER), max(handover, next_opening)
    if day.weekday() == 5:
        return _at(day, _closing(schedule, day)), handover
    return _at(day, _closing(schedule, day)), max(handover, next_opening)
