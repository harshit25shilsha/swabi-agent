from app.services.swabi_client import swabi_client


async def get_all_activities():
    return await swabi_client.get(
        "/activity/get_all_activities?activityStatus=true&pageNumber=-1&pageSize=-1"
    )


async def search_activities(
    country: str = None,
    state: str = None,
    category: str = None
):
    data = await get_all_activities()

    activities = data["data"]["content"]

    results = []

    for activity in activities:

        # Filter by country
        if country and activity.get("country") != country:
            continue

        # Filter by state
        if state and activity.get("state") != state:
            continue

        # Filter by category
        if category and activity.get("activityCategory") != category:
            continue

        results.append(activity)

    return results