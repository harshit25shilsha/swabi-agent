"""
Day-by-day itinerary assembly.

This is the real structural gap Day 4 item 4 is about: recommend_trip
already returns activities + packages as flat, unordered lists, but
nothing assembles them into an actual day-by-day plan that respects
each activity's operating hours, weekly closures, and blackout dates.
That's what this module adds.
"""

from datetime import datetime, timedelta, date as date_cls


WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

# A day only has so many reasonable waking hours to fill with paid
# activities. This caps how much we'll pack into one day so the
# itinerary stays plausible rather than scheduling 14 hours of back-
# to-back activities into a single day.
DEFAULT_MAX_HOURS_PER_DAY = 8.0


def _parse_time(value: str):
    """
    Parse Swabi's "HH:MM" time strings (e.g. "08:00", "20:00") into a
    comparable (hour, minute) tuple. Returns None for missing/malformed
    values rather than raising, since some activities may have blank
    or unexpected time fields and we'd rather skip scheduling them
    precisely than crash the whole itinerary.
    """

    if not value:
        return None

    try:
        parsed = datetime.strptime(value.strip(), "%H:%M")
        return parsed.hour, parsed.minute
    except (ValueError, AttributeError):
        return None


def _time_to_minutes(value: str):
    parsed = _parse_time(value)
    if parsed is None:
        return None
    hours, minutes = parsed
    return hours * 60 + minutes


def _is_activity_closed_on(activity: dict, the_date: date_cls):
    """
    True if this activity is closed on the given calendar date, either
    because of a recurring weekly off-day (e.g. "Sunday") or a specific
    one-off blackout date (activityReligiousOffDates), unless that
    blackout has been marked cancelled.
    """

    weekday_name = WEEKDAY_NAMES[the_date.weekday()]

    weekly_off = activity.get("weeklyOff") or []
    if weekday_name in weekly_off:
        return True

    off_dates = activity.get("activityReligiousOffDates") or []
    date_str = the_date.strftime("%d-%m-%Y")

    for off in off_dates:
        if off.get("religiousOffDate") == date_str and not off.get("isCancelled"):
            return True

    return False


def _activity_fits_day(activity: dict, scheduled_today: list, max_hours_per_day: float):
    """
    Checks whether `activity` can still be added to a day that already
    has `scheduled_today` activities on it: enough remaining hour
    budget, and no time-window overlap with anything already scheduled
    that day (when both have parseable start/end times).
    """

    hours = activity.get("activityHours")
    try:
        hours = float(hours)
    except (TypeError, ValueError):
        hours = 0.0

    hours_used = sum(
        float(a.get("activityHours") or 0)
        for a in scheduled_today
    )

    if hours_used + hours > max_hours_per_day:
        return False

    new_start = _time_to_minutes(activity.get("startTime"))
    new_end = _time_to_minutes(activity.get("endTime"))

    if new_start is None or new_end is None:
        # Can't verify a time conflict without parseable times, so we
        # allow it through on hours budget alone rather than blocking
        # an otherwise-valid activity over missing data.
        return True

    for existing in scheduled_today:
        existing_start = _time_to_minutes(existing.get("startTime"))
        existing_end = _time_to_minutes(existing.get("endTime"))

        if existing_start is None or existing_end is None:
            continue

        # Overlap check: two windows [a, b) and [c, d) overlap if
        # a < d and c < b.
        if new_start < existing_end and existing_start < new_end:
            return False

    return True


def build_itinerary(
    activities: list,
    duration: int,
    start_date: str = None,
    max_hours_per_day: float = DEFAULT_MAX_HOURS_PER_DAY
):
    """
    Greedily assign a flat list of Swabi activity dicts to `duration`
    consecutive calendar days, respecting each activity's weekly
    off-days, specific blackout dates, operating-hour window, and a
    per-day hour budget.

    start_date: "DD-MM-YYYY" string. If not given, defaults to
    tomorrow, so weekday/blackout-date checks always have a concrete
    calendar to check against — without an anchor date, "closed on
    Sundays" can't be evaluated against anything meaningful.

    Algorithm: greedy day-fill, activities considered in their given
    order (callers should pre-sort by whatever priority makes sense —
    e.g. price, or category match strength). For each day in order, we
    walk the remaining unscheduled activities and add the first ones
    that fit (not closed that day, fits the remaining hour budget, no
    time-window overlap with anything already placed that day).

    This is intentionally a simple greedy heuristic, not an optimal
    scheduler (e.g. it doesn't try to minimize idle gaps or maximize
    total activities) — that's an appropriate scope for this phase;
    optimality can be revisited later if recommendation quality
    becomes an issue in practice.

    Returns a dict:
        {
            "days": [
                {
                    "day_number": 1,
                    "date": "DD-MM-YYYY",
                    "weekday": "Monday",
                    "activities": [ ...scheduled activity dicts... ],
                    "total_hours": 4.0
                },
                ...
            ],
            "unscheduled_activities": [ ...activities that didn't fit anywhere... ]
        }
    """

    if duration is None or duration < 1:
        duration = 1

    if start_date:
        anchor = datetime.strptime(start_date, "%d-%m-%Y").date()
    else:
        anchor = date_cls.today() + timedelta(days=1)

    remaining = list(activities)
    days = []

    for day_index in range(duration):
        the_date = anchor + timedelta(days=day_index)
        weekday_name = WEEKDAY_NAMES[the_date.weekday()]

        scheduled_today = []
        still_remaining = []

        for activity in remaining:
            if (
                not _is_activity_closed_on(activity, the_date)
                and _activity_fits_day(activity, scheduled_today, max_hours_per_day)
            ):
                scheduled_today.append(activity)
            else:
                still_remaining.append(activity)

        remaining = still_remaining

        days.append({
            "day_number": day_index + 1,
            "date": the_date.strftime("%d-%m-%Y"),
            "weekday": weekday_name,
            "activities": scheduled_today,
            "total_hours": sum(
                float(a.get("activityHours") or 0)
                for a in scheduled_today
            )
        })

    return {
        "days": days,
        "unscheduled_activities": remaining
    }