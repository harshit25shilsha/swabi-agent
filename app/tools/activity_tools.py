from app.services.swabi_client import swabi_client


async def get_all_activities():
    return await swabi_client.get(
        "/activity/get_all_activities?activityStatus=true&pageNumber=-1&pageSize=-1"
    )


async def get_activity_categories():
    """
    Fetch the canonical list of Swabi activity/package category names
    (e.g. "Adventure", "Hiking", "Religious & Pilgrim Tours"). The agent
    should consult this before guessing a category for a filtered search,
    since an incorrect category name causes search_activities /
    search_packages to silently return zero results rather than an error.
    """
    return await swabi_client.get(
        "/activity_category"
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

       
        if city:
            activity_city = activity.get("city", "")
            if not activity_city or city.lower() not in activity_city.lower():
                continue

        
        if max_price is not None:

            activity_price = activity.get("activityPrice", 0)

            try:
                activity_price = float(activity_price)
            except (TypeError, ValueError):
                activity_price = 0

            if activity_price > max_price:
                continue

        results.append(activity)

    return results