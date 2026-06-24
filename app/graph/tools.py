import json
from typing import Optional

from langchain.tools import tool

from app.tools.activity_tools import (
    search_activities,
    get_activity_categories
)

from app.tools.package_tools import (
    search_packages,
    get_package_by_id
)

from app.tools.recommendation_tools import (
    recommend_trip,
    personalized_recommend_trip,
    build_trip_itinerary
)

from app.tools.user_tools import (
    get_user_profile
)

from app.core.token_budget import (
    summarize_activity,
    summarize_package,
    slim_profile
)


@tool
async def activity_search_tool(
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None
):
    """Search activities by location, category, and/or max price per person.
    Use for standalone activity queries. Check activity_category_list_tool
    first if unsure of exact category name."""

    result = await search_activities(
        country=country,
        state=state,
        city=city,
        category=category,
        max_price=max_price
    )

    return "\n".join(summarize_activity(a) for a in result)


@tool
async def package_search_tool(
    category: str
):
    """Search packages by category only. Use trip_recommendation_tool
    instead when location, budget, or duration is also given."""

    result = await search_packages(category=category)
    packages = (result.get("data") or {}).get("content", [])

    return "\n\n".join(summarize_package(p) for p in packages)


@tool
async def package_detail_tool(
    package_id: int
):
    """Get full details for one package by its numeric ID. Use after
    the user selects a specific package from search results."""

    result = await get_package_by_id(package_id)
    package = (result.get("data") or result)

    return summarize_package(package)


@tool
async def trip_recommendation_tool(
    destination: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    max_budget: Optional[float] = None,
    duration: Optional[int] = None
):
    """Recommend activities and packages filtered by destination, category,
    budget, and/or days. Use this for multi-constraint trip queries.
    Use itinerary_planner_tool instead when the user wants a day-by-day plan."""

    result = await recommend_trip(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration
    )

    activities = "\n".join(
        summarize_activity(a) for a in result.get("activities", [])
    )
    packages = "\n\n".join(
        summarize_package(p) for p in result.get("packages", [])
    )

    return f"ACTIVITIES:\n{activities or 'none'}\n\nPACKAGES:\n{packages or 'none'}"


@tool
async def activity_category_list_tool():
    """Return the exact list of valid Swabi category names. Call this
    before any category-filtered search when unsure of exact spelling."""

    result = await get_activity_categories()
    return json.dumps(result, default=str)


@tool
async def user_profile_tool(
    user_id: int
):
    """Return a user's travel preferences, booking history, and recent
    searches. Use when the user asks what you know about them, or to
    explain a personalized recommendation."""

    result = await get_user_profile(user_id)
    return json.dumps(slim_profile(result), default=str)


@tool
async def personalized_trip_recommendation_tool(
    user_id: int,
    destination: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    max_budget: Optional[float] = None,
    duration: Optional[int] = None
):
    """Like trip_recommendation_tool but fills in missing destination/category
    from the user's booking history and preferences. Use when user_id is known
    and the request is open-ended. Explicit args always override profile defaults."""

    result = await personalized_recommend_trip(
        user_id=user_id,
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration
    )

    activities = "\n".join(
        summarize_activity(a) for a in result.get("activities", [])
    )
    packages = "\n\n".join(
        summarize_package(p) for p in result.get("packages", [])
    )
    filters = result.get("resolved_filters", {})

    return (
        f"RESOLVED_FILTERS: {json.dumps(filters)}\n\n"
        f"ACTIVITIES:\n{activities or 'none'}\n\n"
        f"PACKAGES:\n{packages or 'none'}"
    )


@tool
async def itinerary_planner_tool(
    destination: Optional[str] = None,
    category: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    max_budget: Optional[float] = None,
    duration: Optional[int] = None,
    start_date: Optional[str] = None,
    user_id: Optional[int] = None
):
    """Build a day-by-day itinerary scheduling activities onto specific days,
    respecting closures and time overlaps. Use when user wants a PLAN or
    SCHEDULE ('plan my trip', 'day by day', 'build an itinerary').
    start_date format: DD-MM-YYYY. duration defaults to 3 if not given."""

    result = await build_trip_itinerary(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration,
        start_date=start_date,
        user_id=user_id
    )

    lines = []

    if result.get("duration_was_defaulted"):
        lines.append(
            f"NOTE: No duration given, defaulted to "
            f"{result.get('duration_used')} days."
        )

    for day in result.get("itinerary", []):
        day_activities = day.get("activities", [])
        act_lines = "\n  ".join(
            summarize_activity(a) for a in day_activities
        ) or "no activities scheduled"
        lines.append(
            f"Day {day['day_number']} ({day['weekday']}, {day['date']}) "
            f"— {day['total_hours']}h total:\n  {act_lines}"
        )

    unscheduled = result.get("unscheduled_activities", [])
    if unscheduled:
        lines.append(
            f"UNSCHEDULED ({len(unscheduled)} activities couldn't fit):\n  "
            + "\n  ".join(summarize_activity(a) for a in unscheduled)
        )

    packages = "\n\n".join(
        summarize_package(p) for p in result.get("packages", [])
    )
    if packages:
        lines.append(f"PACKAGES:\n{packages}")

    return "\n\n".join(lines)


tools = [
    activity_search_tool,
    package_search_tool,
    package_detail_tool,
    trip_recommendation_tool,
    activity_category_list_tool,
    user_profile_tool,
    personalized_trip_recommendation_tool,
    itinerary_planner_tool
]