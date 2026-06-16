from app.services.swabi_client import swabi_client


async def get_all_activities():
    return await swabi_client.get(
        "/activity/get_all_activities?activityStatus=true&pageNumber=-1&pageSize=-1"
    )


async def search_activities(
    country=None,
    state=None,
    city=None,
    category=None,
    max_price=None
):
    data = await get_all_activities()

    activities = data["data"]["content"]

    results = []

    for activity in activities:

        # Country filter
        if country and (
            activity.get("country", "").lower()
            != country.lower()
        ):
            continue

        # State filter
        if state and (
            activity.get("state", "").lower()
            != state.lower()
        ):
            continue

        # Category filter
        if category and (
            activity.get("activityCategory", "").lower()
            != category.lower()
        ):
            continue

        # City filter
        if city and (
            activity.get("city", "").lower()
            != city.lower()
        ):
            continue

        # Price filter
        if max_price:

            activity_price = activity.get("price", 0)

            try:
                activity_price = float(activity_price)
            except Exception:
                activity_price = 0

            if activity_price > max_price:
                continue

        results.append(activity)

    return results