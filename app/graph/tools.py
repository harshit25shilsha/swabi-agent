import json

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
    personalized_recommend_trip
)

from app.tools.user_tools import (
    get_user_profile
)


@tool
async def activity_search_tool(
    country: str = None,
    state: str = None,
    city: str = None,
    category: str = None,
    max_price: float = None
):
    """
    Search Swabi activities, optionally filtered by country, state, city,
    category, and/or a maximum price per person.

    Use this when the user wants standalone activities/experiences rather
    than a full multi-day package, e.g. "show adventure activities in
    Uttarakhand" or "activities under 2000 rupees in Goa".

    category should be one of Swabi's known activity categories (e.g.
    "Adventure", "Hiking", "Camping", "Swimming", "Scuba Diving"). If
    unsure of the exact category name, call activity_category_list_tool
    first rather than guessing.
    """

    result = await search_activities(
        country=country,
        state=state,
        city=city,
        category=category,
        max_price=max_price
    )

    return json.dumps(
        result,
        default=str
    )


@tool
async def package_search_tool(
    category: str
):
    """
    Search Swabi travel packages by category only (e.g. "Adventure",
    "Religious & Pilgrim Tours"). This does NOT filter by location,
    budget, or trip duration.

    Use trip_recommendation_tool instead when the user also gives a
    destination, budget, or number of days, since this tool can't apply
    those filters.
    """

    result = await search_packages(
        category=category
    )

    return json.dumps(
        result,
        default=str
    )


@tool
async def package_detail_tool(
    package_id: int
):
    """
    Get full details for a single Swabi package by its numeric package
    ID, including its activities, vendor, price, and duration. Use this
    after the user picks a specific package from search results.
    """

    result = await get_package_by_id(
        package_id
    )

    return json.dumps(
        result,
        default=str
    )


@tool
async def trip_recommendation_tool(
    destination: str = None,
    category: str = None,
    country: str = None,
    state: str = None,
    max_budget: float = None,
    duration: int = None
):
    """
    Recommend both activities and packages for a trip, filtered by
    destination, category, budget, and/or trip length in days.

    destination is a convenience field: pass it when the user names a
    single place (e.g. "Uttarakhand", "Goa", "India") without specifying
    whether it's a country or a state — it will be matched against state
    first, then country. Pass country/state explicitly instead if you
    already know which one it is.

    Use this (rather than activity_search_tool or package_search_tool
    individually) whenever the user describes a trip with multiple
    constraints, e.g. "plan a 5 day adventure trip in Uttarakhand under
    8000 rupees".
    """

    result = await recommend_trip(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration
    )

    return json.dumps(
        result,
        default=str
    )


@tool
async def activity_category_list_tool():
    """
    Look up the exact list of valid Swabi activity/package category
    names. Call this BEFORE activity_search_tool, package_search_tool,
    or trip_recommendation_tool whenever the user's category wording
    might not match Swabi's exact category name (e.g. user says
    "pilgrimage" but the real category is "Religious & Pilgrim Tours").
    Passing a category name that doesn't exactly match returns zero
    results rather than an error, so checking first avoids silently
    empty responses.
    """

    result = await get_activity_categories()

    return json.dumps(
        result,
        default=str
    )


@tool
async def user_profile_tool(
    user_id: int
):
    """
    Look up what Swabi knows about a specific user: their explicitly
    stated travel preferences, categories/states they've actually
    booked before, recently searched destinations, and recently viewed
    packages.

    Use this when the user asks what you know about their preferences
    or past activity, or when you want to explain why a recommendation
    was personalized to them. For getting an actual recommendation,
    prefer personalized_trip_recommendation_tool, which uses this same
    data automatically.
    """

    result = await get_user_profile(
        user_id
    )

    return json.dumps(
        result,
        default=str
    )


@tool
async def personalized_trip_recommendation_tool(
    user_id: int,
    destination: str = None,
    category: str = None,
    country: str = None,
    state: str = None,
    max_budget: float = None,
    duration: int = None
):
    """
    Like trip_recommendation_tool, but fills in destination/category
    from the user's own profile (past bookings, search history, stated
    preferences) for any field the caller didn't explicitly provide.

    Always pass any destination, category, budget, or duration the
    user explicitly mentioned in their message — those values always
    take priority over profile defaults. Only leave a field unset if
    the user didn't specify it and you want this tool to infer a
    sensible default from their history.

    Use this instead of trip_recommendation_tool whenever a user_id is
    known and the user's request is open-ended (e.g. "recommend me a
    trip", "what should I book next").
    """

    result = await personalized_recommend_trip(
        user_id=user_id,
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration
    )

    return json.dumps(
        result,
        default=str
    )


tools = [
    activity_search_tool,
    package_search_tool,
    package_detail_tool,
    trip_recommendation_tool,
    activity_category_list_tool,
    user_profile_tool,
    personalized_trip_recommendation_tool
]