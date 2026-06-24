"""
Token budget management for LLM tool results.

Two levels of compression are available:

slim_*    — strip noisy fields (images, timestamps, vendor objects)
             but keep JSON structure. Used internally where structure
             matters (e.g. passing data between Python functions).

summarize_* — collapse each object to a single pipe-delimited line.
               Used at the final tool serialization step before
               sending to Groq. ~75% smaller than slim_* output,
               which is the main lever for reducing token usage.

Pipeline:
  Swabi API (full JSON)
    → slim_* (strip noise, keep structure for Python logic)
    → summarize_* (collapse to line for LLM consumption)
    → json.dumps → Groq
"""


def slim_activity(activity: dict) -> dict:
    """Strip noisy fields, keep structured dict for internal use."""

    return {
        "activityId": activity.get("activityId"),
        "activityName": activity.get("activityName"),
        "country": activity.get("country"),
        "state": activity.get("state"),
        "city": activity.get("city"),
        "activityCategory": activity.get("activityCategory"),
        "activityPrice": activity.get("activityPrice"),
        "currency": activity.get("currency"),
        "activityHours": activity.get("activityHours"),
        "startTime": activity.get("startTime"),
        "endTime": activity.get("endTime"),
        "bestTimeToVisit": activity.get("bestTimeToVisit"),
        "description": (activity.get("description") or "")[:200],
        "participantType": activity.get("participantType"),
        "weeklyOff": activity.get("weeklyOff"),
        "activityReligiousOffDates": [
            {
                "religiousOffDate": d.get("religiousOffDate"),
                "isCancelled": d.get("isCancelled")
            }
            for d in (activity.get("activityReligiousOffDates") or [])
        ]
    }


def summarize_activity(activity: dict) -> str:
    """
    Collapse an activity to a single pipe-delimited line for LLM
    consumption. ~75% smaller than slim_activity JSON output.

    Fields included (all the LLM needs for recommendations):
      id | name | category | state, country | price currency | hours |
      open startTime-endTime | best season | weekly-off | description
    """

    off_dates = [
        d.get("religiousOffDate")
        for d in (activity.get("activityReligiousOffDates") or [])
        if d.get("religiousOffDate") and not d.get("isCancelled")
    ]

    weekly_off = activity.get("weeklyOff") or []
    closures = ", ".join(weekly_off + off_dates) or "none"

    price = activity.get("activityPrice")
    currency = activity.get("currency") or "INR"
    price_str = f"{price} {currency}" if price is not None else "?"

    desc = (activity.get("description") or "").strip()[:100]

    return (
        f"id={activity.get('activityId')} | "
        f"{activity.get('activityName')} | "
        f"{activity.get('activityCategory')} | "
        f"{activity.get('state')}, {activity.get('country')} | "
        f"{price_str} | "
        f"{activity.get('activityHours')}h | "
        f"{activity.get('startTime')}-{activity.get('endTime')} | "
        f"best:{activity.get('bestTimeToVisit')} | "
        f"closed:{closures} | "
        f"{desc}"
    )


def summarize_package(package: dict) -> str:
    """
    Collapse a package to a compact multi-line block for LLM
    consumption. Header line with key fields, then one line per
    included activity. ~75% smaller than slim_package JSON output.
    """

    price = package.get("totalPrice")
    currency = package.get("currency") or "INR"
    price_str = f"{price} {currency}" if price is not None else "?"

    lines = [
        f"pkg={package.get('packageId')} | "
        f"{package.get('packageName')} | "
        f"{package.get('noOfDays')} days | "
        f"{price_str} | "
        f"{package.get('state') or package.get('country') or '?'}"
    ]

    for pa in (package.get("packageActivities") or []):
        activity = pa.get("activity") or {}
        a_price = activity.get("activityPrice")
        a_currency = activity.get("currency") or "INR"
        lines.append(
            f"  - {activity.get('activityName')} | "
            f"{activity.get('activityCategory')} | "
            f"{activity.get('state')} | "
            f"{a_price} {a_currency} | "
            f"{activity.get('activityHours')}h"
        )

    return "\n".join(lines)


def slim_profile(profile: dict) -> dict:
    """Minimal user profile dict for LLM personalization decisions."""

    prefs = profile.get("explicit_preferences") or {}

    return {
        "userId": profile.get("userId"),
        "explicit_preferences": {
            "activity_types": (prefs.get("activity_types") or [])[:5],
            "countries": (prefs.get("countries") or [])[:5],
            "place_types": (prefs.get("place_types") or [])[:5],
            "trip_purposes": (prefs.get("trip_purposes") or [])[:5],
            "season": (prefs.get("season") or [])[:3],
            "trip_duration": (prefs.get("trip_duration") or [])[:2],
        } if prefs else None,
        "booked_categories": profile.get("booked_categories", []),
        "booked_states": profile.get("booked_states", []),
        "searched_states": (profile.get("searched_states") or [])[:5],
        "searched_countries": (profile.get("searched_countries") or [])[:5],
        "viewed_package_ids": (profile.get("viewed_package_ids") or [])[:5],
        "raw_booking_count": profile.get("raw_booking_count", 0)
    }