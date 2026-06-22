from app.tools.activity_tools import (
    search_activities
)

from app.tools.package_tools import (
    recommend_packages
)

from app.tools.user_tools import (
    get_user_profile
)

from app.tools.itinerary_tools import build_itinerary

async def recommend_trip(
    destination: str = None,
    category: str = None,
    country: str = None,
    state: str = None,
    max_budget: float = None,
    duration: int = None
):
    """
    Recommend activities and packages for a trip.

    `destination` is a convenience field for callers (including the LLM)
    who just say a single place name without knowing whether it's a
    country or a state. If `country`/`state` aren't given explicitly,
    `destination` is tried against state first (most Swabi destinations
    in the sample data are states like "Uttarakhand" or "Goa"), and
    against country if nothing more specific was supplied.
    """

    resolved_state = state or destination
    resolved_country = country

    activities = await search_activities(
        country=resolved_country,
        state=resolved_state,
        category=category,
        max_price=max_budget
    )

    packages = await recommend_packages(
        category=category,
        country=resolved_country,
        state=resolved_state,
        max_budget=max_budget,
        duration=duration
    )

    return {
        "activities": activities,
        "packages": packages
    }


def _first_or_none(values):
    return values[0] if values else None


async def personalized_recommend_trip(
    user_id: int,
    destination: str = None,
    category: str = None,
    country: str = None,
    state: str = None,
    max_budget: float = None,
    duration: int = None
):
    """
    Same as recommend_trip, but fills in destination/category from the
    user's profile (booking history, search history, explicit stated
    preferences) whenever the caller didn't already specify them.

    Precedence per field (most specific / most intentional wins):
    - category: explicit arg > a category the user has actually
      booked before > a category from their stated preferences
    - location (state/country): explicit arg/destination > a state
      the user has actually booked before > a state they've recently
      searched for > a country from their stated preferences

    This is intentionally simple substitution, not weighted scoring.
    If the caller already gave a value for a field, the profile is
    never consulted for that field — explicit user input in the
    current message always overrides profile-derived defaults.
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
    resolved_state = state
    resolved_country = country

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
        duration=duration
    )

    result["resolved_filters"] = {
        "category": resolved_category,
        "country": resolved_country,
        "state": resolved_state,
        "destination": resolved_destination,
        "source": "personalized"
    }

    return result


DEFAULT_ITINERARY_DURATION = 3

async def build_trip_itinerary(
    destination: str = None,
    category: str = None,
    country: str = None,
    state: str = None,
    max_budget : float = None,
    duration: int = None,
    start_date: str = None,
    user_id: int = None
):
    """
    The real multi-tool orchestration step: finds matching activities
    (and packages, for reference/pricing context) via the existing
    search tools, THEN assembles the activities into an actual
    day-by-day schedule via build_itinerary, respecting each
    activity's operating hours, weekly off-days, and blackout dates.

    This is what turns "here are some activities and some packages,
    good luck" into an actual structured travel plan — previously
    recommend_trip / personalized_recommend_trip only returned flat,
    unordered lists with no notion of which day anything happens on.

    If user_id is given, activity/package search is personalized via
    the same precedence rules as personalized_recommend_trip (explicit
    args > booking history > search history > stated preferences).

    duration defaults to 3 days if not given, since itinerary
    scheduling needs a concrete day count — the resolved duration used
    is always included in the response so callers (and the LLM) can
    see when a default was applied rather than something the user
    actually asked for.
    """
    
    resolved_duration = duration if duration and duration >=1 else DEFAULT_ITINERARY_DURATION
    
    if user_id is not None:
        trip = await personalized_recommend_trip(
            user_id=user_id,
            destination=destination,
            category=category,
            country = country,
            state = state,
            max_budget=max_budget,
            duration=resolved_duration
        )
        
    else:
        trip = await recommend_trip(
            destination=destination,
            category=category,
            country=country,
            state=state,
            max_budget=max_budget,
            duration = resolved_duration
        )
    schedule = build_itinerary(
        activities=trip["activities"],
        duration = resolved_duration,
        start_date=start_date
    )
    
    return {
        "duration_used": resolved_duration,
        "duration_was_defaulted": duration is None or duration < 1,
        "itinerary": schedule["days"],
        "unscheduled_activities":schedule["unscheduled_activities"],
        "packages": trip["packages"],
        "resolved_filters": trip.get("resolved_filters", {
            "category": category,
            "country": country,
            "state":state,
            "destination":destination,
            "source": "explicit"
        })
    }
        
    
