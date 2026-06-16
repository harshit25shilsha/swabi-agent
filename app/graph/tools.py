import json

from langchain.tools import tool

from app.tools.activity_tools import (
    search_activities
)

from app.tools.package_tools import (
    search_packages,
    get_package_by_id
)

from app.tools.recommendation_tools import (
    recommend_trip
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
    Search activities.
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
    Search packages by category.
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
    Get package details by package id.
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
    destination: str,
    category: str = None
):
    """
    Recommend activities and packages
    for a destination.
    """

    result = await recommend_trip(
        destination,
        category
    )

    return json.dumps(
        result,
        default=str
    )


tools = [
    activity_search_tool,
    package_search_tool,
    package_detail_tool,
    trip_recommendation_tool
]
