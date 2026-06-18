from app.services.swabi_client import swabi_client


async def get_travel_preferences(user_id: int = None):
    """
    Fetch Swabi travel preferences.

    NOTE on response shape: unlike most Swabi endpoints, this one
    returns a bare JSON array (no {"status": ..., "data": ...}
    envelope) — confirmed from the sample response for
    /api/travel/get_all_travel_preferences. There is currently no
    per-user filtering on the Swabi side, so we fetch everyone's
    preferences and filter by userId here.

    When user_id is given, returns the single matching preferences
    record as a dict, or None if the user has never set preferences
    (each user has at most one preferences record in the sample data).
    When user_id is None, returns the full list for all users.
    """

    all_preferences = await swabi_client.get(
        "/travel/get_all_travel_preferences"
    )

    if user_id is None:
        return all_preferences

    for pref in all_preferences:
        if pref.get("userId") == user_id:
            return pref

    return None


async def get_user_bookings(user_id: int, booking_status: str = "ALL"):
    """
    Fetch a user's package bookings (booked, pending, cancelled, etc.
    depending on booking_status). Uses Swabi's per-user booking
    endpoint, which already returns the standard {status, data:
    {content: [...]}} envelope.
    """

    return await swabi_client.get(
        f"/package_booking/get_package_booking_by_userId"
        f"?userId={user_id}&bookingStatus={booking_status}"
        f"&pageNumber=0&pageSize=20&sortBy=bookingId&sortDirection=desc&search="
    )


async def get_search_logs(user_id: int = None, limit: int = 20):
    """
    Fetch package search event logs (country/state searched, when).
    Swabi doesn't expose per-user filtering on this endpoint either,
    so we fetch the full log and filter by userId here.

    Results are sorted newest-first by createdAt (rather than relying
    on the order Swabi happens to return them in) and capped at
    `limit` so a long-lived user's full search history doesn't bloat
    the tool output handed to the LLM.
    """

    raw = await swabi_client.get(
        "/package/get_all_package_search_logs"
    )

    logs = (raw.get("data") or [])

    if user_id is not None:
        logs = [
            log for log in logs
            if log.get("userId") == user_id
        ]

    logs.sort(
        key=lambda log: log.get("createdAt", ""),
        reverse=True
    )

    return logs[:limit]


async def get_view_logs(user_id: int = None, limit: int = 20):
    """
    Fetch package view event logs (which package/activities were
    viewed, when). Same filtering and recency-sort approach as
    get_search_logs.
    """

    raw = await swabi_client.get(
        "/package/get_all_package_view_logs"
    )

    logs = (raw.get("data") or [])

    if user_id is not None:
        logs = [
            log for log in logs
            if log.get("userId") == user_id
        ]

    logs.sort(
        key=lambda log: log.get("createdAt", ""),
        reverse=True
    )

    return logs[:limit]


def _booking_categories_and_states(bookings_payload: dict):
    """
    Pull out the set of activity categories and states the user has
    actually booked in the past, by walking each booking's nested
    pkg.packageActivities[].activity, the same nested shape used in
    package_tools._package_locations.
    """

    categories = set()
    states = set()

    bookings = (bookings_payload.get("data") or {}).get("content", [])

    for booking in bookings:
        pkg = booking.get("pkg") or {}

        for pa in pkg.get("packageActivities", []) or []:
            activity = pa.get("activity") or {}

            category = activity.get("activityCategory")
            if category:
                categories.add(category)

            state = activity.get("state")
            if state:
                states.add(state)

    return sorted(categories), sorted(states)


async def get_user_profile(user_id: int):
    """
    Aggregate everything we know about a single user into one
    normalized shape: explicit stated preferences, categories/states
    inferred from past bookings, and recently searched/viewed
    countries/states.

    This is read-only aggregation for Phase 2 — it does NOT compute a
    weighted recommendation score (explicit > booking > view > search).
    That scoring logic is intentionally deferred to a later phase so
    this stays a simple, inspectable data assembly step.
    """

    preferences = await get_travel_preferences(user_id)
    bookings = await get_user_bookings(user_id)
    search_logs = await get_search_logs(user_id)
    view_logs = await get_view_logs(user_id)

    booked_categories, booked_states = _booking_categories_and_states(bookings)

    # get_search_logs() already returns logs newest-first by createdAt.
    # We preserve that recency order here (dict.fromkeys dedupes while
    # keeping first-seen order) rather than alphabetically sorting, since
    # "most recently searched" is a meaningfully different and more
    # useful signal than "alphabetically first searched" for picking a
    # default destination.
    searched_states = list(dict.fromkeys(
        log.get("state") for log in search_logs
        if log.get("state")
    ))
    searched_countries = list(dict.fromkeys(
        log.get("country") for log in search_logs
        if log.get("country")
    ))

    viewed_package_ids = [
        log.get("packageId") for log in view_logs
        if log.get("packageId") is not None
    ]

    return {
        "userId": user_id,
        "explicit_preferences": preferences,
        "booked_categories": booked_categories,
        "booked_states": booked_states,
        "searched_states": searched_states,
        "searched_countries": searched_countries,
        "viewed_package_ids": viewed_package_ids,
        "raw_booking_count": len(
            (bookings.get("data") or {}).get("content", [])
        ),
    }