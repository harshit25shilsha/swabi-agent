"""
Token budget management for LLM tool results.

Pipeline:
  Swabi API (full JSON)
    → slim_*  (internal use — keeps structure for Python logic)
    → summarize_* (one compact line/block per object — sent to LLM)
    → Groq

Result caps keep each tool response small by default:
  TOP_N_ACTIVITIES  — cap for flat activity lists (search / recommend)
  TOP_N_PACKAGES    — cap for flat package lists
  TOP_N_PKG_ACTS    — activities shown per package in search summaries
  TOP_N_PKG_DETAIL  — activities shown per package in detail view
"""

TOP_N_ACTIVITIES = 5   # search / recommend results
TOP_N_PACKAGES   = 3   # search / recommend results
TOP_N_PKG_ACTS   = 3   # nested activities shown in search summary
TOP_N_PKG_DETAIL = 6   # nested activities shown in full detail view


# ── Internal slim helpers (used between Python functions) ──────────────────

def slim_activity(activity: dict) -> dict:
    """Strip noisy fields; keep structured dict for internal scheduling logic."""
    return {
        "activityId":                activity.get("activityId"),
        "activityName":              activity.get("activityName"),
        "country":                   activity.get("country"),
        "state":                     activity.get("state"),
        "city":                      activity.get("city"),
        "activityCategory":          activity.get("activityCategory"),
        "activityPrice":             activity.get("activityPrice"),
        "currency":                  activity.get("currency"),
        "activityHours":             activity.get("activityHours"),
        "startTime":                 activity.get("startTime"),
        "endTime":                   activity.get("endTime"),
        "bestTimeToVisit":           activity.get("bestTimeToVisit"),
        "description":               (activity.get("description") or "")[:200],
        "participantType":           activity.get("participantType"),
        "weeklyOff":                 activity.get("weeklyOff"),
        "activityReligiousOffDates": [
            {
                "religiousOffDate": d.get("religiousOffDate"),
                "isCancelled":      d.get("isCancelled"),
            }
            for d in (activity.get("activityReligiousOffDates") or [])
        ],
    }


# ── LLM-facing summarizers ─────────────────────────────────────────────────

def summarize_activity(activity: dict) -> str:
    """
    Single pipe-delimited line per activity for LLM consumption.
    ~75 % smaller than slim_activity JSON. Used in search, recommend,
    and itinerary tool responses.
    """
    off_dates = [
        d.get("religiousOffDate")
        for d in (activity.get("activityReligiousOffDates") or [])
        if d.get("religiousOffDate") and not d.get("isCancelled")
    ]
    weekly_off = activity.get("weeklyOff") or []
    closures   = ", ".join(weekly_off + off_dates) or "none"

    price     = activity.get("activityPrice")
    currency  = activity.get("currency") or "INR"
    price_str = f"{price} {currency}" if price is not None else "?"

    desc = (activity.get("description") or "").strip()[:80]

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


def summarize_package(package: dict, *, detail: bool = False) -> str:
    """
    Compact multi-line block per package for LLM consumption.

    detail=False (search results): header + top TOP_N_PKG_ACTS activities.
    detail=True  (package_detail_tool): header + top TOP_N_PKG_DETAIL
                 activities + description snippet.
    """
    price     = package.get("totalPrice")
    currency  = package.get("currency") or "INR"
    price_str = f"{price} {currency}" if price is not None else "?"

    loc = package.get("state") or package.get("country") or "?"

    lines = [
        f"pkg={package.get('packageId')} | "
        f"{package.get('packageName')} | "
        f"{package.get('noOfDays')} days | "
        f"{price_str} | "
        f"{loc}"
    ]

    if detail:
        desc = (package.get("description") or "").strip()[:120]
        if desc:
            lines.append(f"  desc: {desc}")

    cap = TOP_N_PKG_DETAIL if detail else TOP_N_PKG_ACTS
    acts = (package.get("packageActivities") or [])[:cap]

    for pa in acts:
        activity  = pa.get("activity") or {}
        a_price   = activity.get("activityPrice")
        a_currency = activity.get("currency") or "INR"
        lines.append(
            f"  - {activity.get('activityName')} | "
            f"{activity.get('activityCategory')} | "
            f"{activity.get('state')} | "
            f"{a_price} {a_currency} | "
            f"{activity.get('activityHours')}h"
        )

    total_acts = len(package.get("packageActivities") or [])
    if total_acts > cap:
        lines.append(f"  ... +{total_acts - cap} more activities")

    return "\n".join(lines)


def slim_profile(profile: dict) -> dict:
    """Minimal user-profile dict for LLM personalization decisions."""
    prefs = profile.get("explicit_preferences") or {}
    return {
        "userId": profile.get("userId"),
        "explicit_preferences": {
            "activity_types": (prefs.get("activity_types") or [])[:5],
            "countries":      (prefs.get("countries") or [])[:5],
            "place_types":    (prefs.get("place_types") or [])[:5],
            "trip_purposes":  (prefs.get("trip_purposes") or [])[:5],
            "season":         (prefs.get("season") or [])[:3],
            "trip_duration":  (prefs.get("trip_duration") or [])[:2],
        } if prefs else None,
        "booked_categories":   profile.get("booked_categories", []),
        "booked_states":       profile.get("booked_states", []),
        "searched_states":     (profile.get("searched_states") or [])[:5],
        "searched_countries":  (profile.get("searched_countries") or [])[:5],
        "viewed_package_ids":  (profile.get("viewed_package_ids") or [])[:5],
        "raw_booking_count":   profile.get("raw_booking_count", 0),
    }