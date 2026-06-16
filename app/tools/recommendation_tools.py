from app.tools.activity_tools import (
    search_activities
)

from app.tools.package_tools import (
    recommend_packages
)


async def recommend_trip(
    destination: str,
    category: str = None
):

    activities = await search_activities(
        state=destination,
        category=category
    )

    packages = await recommend_packages(
        state=destination,
        category=category
    )

    return {
        "activities": activities,
        "packages": packages
    }