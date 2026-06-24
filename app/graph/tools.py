import json
from typing import Optional, Union

from langchain.tools import tool

from app.tools.activity_tools import (
    search_activities,
    get_activity_categories,
)
from app.tools.package_tools import (
    search_packages,
    get_package_by_id,
)
from app.tools.recommendation_tools import (
    recommend_trip,
    personalized_recommend_trip,
    build_trip_itinerary,
)
from app.tools.user_tools import get_user_profile
from app.core.token_budget import (
    summarize_activity,
    summarize_package,
    slim_profile,
    TOP_N_ACTIVITIES,
    TOP_N_PACKAGES,
)


def _to_float(value) -> Optional[float]:
    """
    Coerce LLM-supplied price/budget values to float.

    Groq sometimes generates tool arguments as strings even when the schema
    says float (e.g. max_price="3000" instead of 3000). This causes a 400
    tool_use_failed error. Coercing here means the tool always receives a
    proper float regardless of what the LLM emitted.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    """Same coercion for integer fields (duration, package_id, user_id)."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Activity tools 

@tool
async def activity_search_tool(
    country:   Optional[str]            = None,
    state:     Optional[str]            = None,
    city:      Optional[str]            = None,
    category:  Optional[str]            = None,
    max_price: Optional[Union[float, str]] = None,
):
    """Search activities by location/category/max price. Returns top results.
    Call activity_category_list_tool first when the exact category name is
    uncertain. Use trip_recommendation_tool for multi-constraint queries."""

    results = await search_activities(
        country=country,
        state=state,
        city=city,
        category=category,
        max_price=_to_float(max_price),
    )
    capped = results[:TOP_N_ACTIVITIES]
    lines  = [summarize_activity(a) for a in capped]
    if len(results) > TOP_N_ACTIVITIES:
        lines.append(f"... +{len(results) - TOP_N_ACTIVITIES} more (refine filters to narrow)")
    return "\n".join(lines) or "No activities found."


@tool
async def activity_category_list_tool():
    """Return valid Swabi category names. Call before any category-filtered
    search when unsure of exact spelling."""

    result = await get_activity_categories()
    return json.dumps(result, default=str)


#  Package tools 

@tool
async def package_search_tool(category: str):
    """Search packages by category. Use trip_recommendation_tool when
    location, budget, or duration is also given."""

    result   = await search_packages(category=category)
    packages = (result.get("data") or {}).get("content", [])
    capped   = packages[:TOP_N_PACKAGES]
    lines    = [summarize_package(p) for p in capped]
    if len(packages) > TOP_N_PACKAGES:
        lines.append(f"... +{len(packages) - TOP_N_PACKAGES} more packages")
    return "\n\n".join(lines) or "No packages found."


@tool
async def package_detail_tool(package_id: Union[int, str]):
    """Full details for one package by numeric ID. Use after the user picks
    a specific package from search results."""

    result  = await get_package_by_id(_to_int(package_id))
    package = result.get("data") or result
    return summarize_package(package, detail=True)


#  Recommendation tools 

@tool
async def trip_recommendation_tool(
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
):
    """Recommend activities + packages filtered by destination, category,
    budget, and/or days. Use for multi-constraint trip queries.
    Use itinerary_planner_tool when the user wants a day-by-day plan."""

    result = await recommend_trip(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
    )

    acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
    pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
    act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
    pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

    return (
        f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
        f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
    )


@tool
async def personalized_trip_recommendation_tool(
    user_id:     Union[int, str],
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
):
    """Like trip_recommendation_tool but fills missing destination/category
    from the user's booking history and preferences. Use when user_id is
    known and the request is open-ended. Explicit args override profile."""

    result = await personalized_recommend_trip(
        user_id=_to_int(user_id),
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
    )

    acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
    pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
    filters   = result.get("resolved_filters", {})

    act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
    pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

    return (
        f"RESOLVED_FILTERS: {json.dumps(filters)}\n\n"
        f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
        f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
    )


#  Itinerary tool 

@tool
async def itinerary_planner_tool(
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
    start_date:  Optional[str]            = None,
    user_id:     Optional[Union[int, str]]   = None,
):
    """Build a day-by-day itinerary scheduling activities onto specific days,
    respecting closures and time overlaps. Use for PLAN/SCHEDULE requests
    ('plan my trip', 'day by day', 'build an itinerary').
    start_date format: DD-MM-YYYY. duration defaults to 3."""

    result = await build_trip_itinerary(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
        start_date=start_date,
        user_id=_to_int(user_id),
    )

    lines = []

    if result.get("duration_was_defaulted"):
        lines.append(
            f"NOTE: duration not specified — defaulted to "
            f"{result.get('duration_used')} days."
        )

    for day in result.get("itinerary", []):
        day_acts  = day.get("activities", [])
        act_lines = "\n  ".join(
            summarize_activity(a) for a in day_acts
        ) or "no activities scheduled"
        lines.append(
            f"Day {day['day_number']} ({day['weekday']}, {day['date']}) "
            f"— {day['total_hours']}h:\n  {act_lines}"
        )

    unscheduled = result.get("unscheduled_activities", [])
    if unscheduled:
        names = ", ".join(a.get("activityName", "?") for a in unscheduled[:5])
        extra = f" (+{len(unscheduled) - 5} more)" if len(unscheduled) > 5 else ""
        lines.append(f"UNSCHEDULED ({len(unscheduled)}): {names}{extra}")

    pkgs = result.get("packages", [])[:TOP_N_PACKAGES]
    if pkgs:
        pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs)
        lines.append(f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}")

    return "\n\n".join(lines) or "No itinerary could be built."


# User profile tool 

@tool
async def user_profile_tool(user_id: Union[int, str]):
    """Return a user's travel preferences and booking history summary.
    Use when the user asks what you know about them, or to explain a
    personalized recommendation."""

    result = await get_user_profile(_to_int(user_id))
    return json.dumps(slim_profile(result), default=str)


#  Tool registry 

tools = [
    activity_search_tool,
    activity_category_list_tool,
    package_search_tool,
    package_detail_tool,
    trip_recommendation_tool,
    personalized_trip_recommendation_tool,
    itinerary_planner_tool,
    user_profile_tool,
]