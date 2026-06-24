from app.tools.activity_tools import search_activities
from app.tools.package_tools import recommend_packages
from app.tools.user_tools import get_user_profile
from app.tools.itinerary_tools import build_itinerary

DEFAULT_ITINERARY_DURATION = 3


def _first_or_none(values):
    return values[0] if values else None


async def recommend_trip(
    destination: str   = None,
    category:    str   = None,
    country:     str   = None,
    state:       str   = None,
    max_budget:  float = None,
    duration:    int   = None,
    *,
    # When True (used by itinerary builder), return the full untruncated
    # activity pool so the scheduler can fill multiple days optimally.
    # When False (used by tool layer), the default caps apply.
    full_pool:   bool  = False,
):
    """
    Recommend activities and packages for a trip.

    `destination` is tried against state first (most Swabi destinations
    are states like "Uttarakhand" or "Goa"), then country if no state
    match was given explicitly.
    """
    resolved_state   = state or destination
    resolved_country = country

    activity_limit = None if full_pool else None  # search_activities has its own default cap
    activities = await search_activities(
        country=resolved_country,
        state=resolved_state,
        category=category,
        max_price=max_budget,
        limit=None if full_pool else None,  # cap applied at tool layer via token_budget
    )

    packages = await recommend_packages(
        category=category,
        country=resolved_country,
        state=resolved_state,
        max_budget=max_budget,
        duration=duration,
        limit=None,  # cap applied at tool layer
    )

    return {"activities": activities, "packages": packages}


async def personalized_recommend_trip(
    user_id:     int,
    destination: str   = None,
    category:    str   = None,
    country:     str   = None,
    state:       str   = None,
    max_budget:  float = None,
    duration:    int   = None,
    *,
    full_pool:   bool  = False,
):
    """
    Same as recommend_trip, but fills in destination/category from the
    user's profile when not explicitly provided.

    Precedence (most specific wins):
    - category: explicit arg > booked categories > stated preferences
    - location: explicit arg/destination > booked states > searched
                states > preferred countries
    """
    profile = await get_user_profile(user_id)

    resolved_category = category
    if resolved_category is None:
        resolved_category = _first_or_none(profile["booked_categories"])
    if resolved_category is None:
        prefs = profile["explicit_preferences"]
        if prefs:
            resolved_category = _first_or_none(prefs.get("activity_types") or [])

    resolved_destination = destination
    resolved_state       = state
    resolved_country     = country

    if not (resolved_destination or resolved_state or resolved_country):
        resolved_state = _first_or_none(profile["booked_states"])
        if resolved_state is None:
            resolved_state = _first_or_none(profile["searched_states"])
        if resolved_state is None:
            prefs = profile["explicit_preferences"]
            if prefs:
                resolved_country = _first_or_none(prefs.get("countries") or [])

    result = await recommend_trip(
        destination=resolved_destination,
        category=resolved_category,
        country=resolved_country,
        state=resolved_state,
        max_budget=max_budget,
        duration=duration,
        full_pool=full_pool,
    )

    result["resolved_filters"] = {
        "category":    resolved_category,
        "country":     resolved_country,
        "state":       resolved_state,
        "destination": resolved_destination,
        "source":      "personalized",
    }
    return result


async def build_trip_itinerary(
    destination: str   = None,
    category:    str   = None,
    country:     str   = None,
    state:       str   = None,
    max_budget:  float = None,
    duration:    int   = None,
    start_date:  str   = None,
    user_id:     int   = None,
):
    """
    Fetch matching activities (full untruncated pool), schedule them
    day-by-day via build_itinerary (respecting closures, hours, overlaps),
    and return a structured plan. Packages are returned for context/pricing.

    duration defaults to DEFAULT_ITINERARY_DURATION if not given.
    full_pool=True ensures the scheduler receives all candidate activities,
    not the capped subset that the LLM-facing tools return — the cap is
    applied only at the final summarization step in itinerary_planner_tool.
    """
    resolved_duration = (
        duration if duration and duration >= 1 else DEFAULT_ITINERARY_DURATION
    )

    if user_id is not None:
        trip = await personalized_recommend_trip(
            user_id=user_id,
            destination=destination,
            category=category,
            country=country,
            state=state,
            max_budget=max_budget,
            duration=resolved_duration,
            full_pool=True,
        )
    else:
        trip = await recommend_trip(
            destination=destination,
            category=category,
            country=country,
            state=state,
            max_budget=max_budget,
            duration=resolved_duration,
            full_pool=True,
        )

    # build_itinerary works on full API dicts (needs weeklyOff, startTime,
    # endTime, activityReligiousOffDates for scheduling) — do NOT slim
    # activities before passing here.
    schedule = build_itinerary(
        activities=trip["activities"],
        duration=resolved_duration,
        start_date=start_date,
    )

    return {
        "duration_used":          resolved_duration,
        "duration_was_defaulted": duration is None or duration < 1,
        "itinerary":              schedule["days"],
        "unscheduled_activities": schedule["unscheduled_activities"],
        "packages":               trip["packages"],
        "resolved_filters":       trip.get("resolved_filters", {
            "category":    category,
            "country":     country,
            "state":       state,
            "destination": destination,
            "source":      "explicit",
        }),
    }