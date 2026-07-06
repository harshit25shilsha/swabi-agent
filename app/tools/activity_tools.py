from app.services.swabi_client import swabi_client
from app.core.token_budget import TOP_N_ACTIVITIES


async def get_all_activities():
    return await swabi_client.get(
        "/activity/get_all_activities?activityStatus=true&pageNumber=-1&pageSize=-1"
    )


async def get_activity_by_id(activity_id: int):
    """
    Fetch a single activity by ID. Swabi has no per-ID activity endpoint,
    so this filters client-side from the full activity list — same
    approach as get_travel_preferences/get_search_logs in user_tools.py.
    Returns None if not found.
    """
    data = await get_all_activities()
    activities = (data.get("data") or {}).get("content", [])
    for activity in activities:
        if activity.get("activityId") == activity_id:
            return activity
    return None


async def get_activity_categories():
    """Fetch canonical Swabi category names (e.g. 'Adventure', 'Hiking').
    Consult before guessing a category for filtered searches — an incorrect
    name silently returns zero results."""
    return await swabi_client.get("/activity_category")


async def search_activities(
    country:   str   = None,
    state:     str   = None,
    city:      str   = None,
    category:  str   = None,
    max_price: float = None,
    limit:     int   = TOP_N_ACTIVITIES,
):
    """
    Filter activities from Swabi's full activity list.

    `limit` caps the returned list so callers (and ultimately the LLM)
    don't receive hundreds of raw API dicts. Itinerary scheduling passes
    limit=None to get the full untruncated set it needs for day-filling;
    tool-layer calls use the default TOP_N_ACTIVITIES cap.
    """
    data       = await get_all_activities()
    activities = data["data"]["content"]

    results = []
    for activity in activities:

        if country and (
            activity.get("country", "").lower() != country.lower()
        ):
            continue

        if state and (
            activity.get("state", "").lower() != state.lower()
        ):
            continue

        if category and (
            activity.get("activityCategory", "").lower() != category.lower()
        ):
            continue

        if city:
            activity_city = activity.get("city", "")
            if not activity_city or city.lower() not in activity_city.lower():
                continue

        if max_price is not None:
            try:
                activity_price = float(activity.get("activityPrice", 0))
            except (TypeError, ValueError):
                activity_price = 0
            if activity_price > max_price:
                continue

        results.append(activity)

    if limit is not None:
        return results[:limit]
    return results