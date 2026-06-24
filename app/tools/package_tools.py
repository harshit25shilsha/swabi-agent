from app.services.swabi_client import swabi_client
from app.core.token_budget import TOP_N_PACKAGES


async def get_package_by_id(package_id: int):
    return await swabi_client.get(
        f"/package/get_package_by_id?packageId={package_id}"
    )


async def get_all_packages():
    return await swabi_client.get(
        "/package/get_package_list_all_vendors"
        "?pageNumber=-1&pageSize=-1&packageStatus=ALL&search=&days=&price="
    )


async def search_packages(category: str = None):
    """Search packages by category; falls back to all packages if no
    category given."""
    if not category:
        return await get_all_packages()
    return await swabi_client.get(
        f"/package/get_package_list_by_category"
        f"?categoryName={category}&pageNumber=-1&pageSize=-1"
    )


def _package_locations(package: dict):
    """
    Return (country, state) pairs from nested packageActivities[].activity.
    Top-level state/country are unreliable in Swabi data; nested activity
    fields carry the real location.
    """
    pairs = set()
    for pa in package.get("packageActivities", []) or []:
        activity = pa.get("activity") or {}
        pairs.add((
            (activity.get("country") or "").lower(),
            (activity.get("state") or "").lower(),
        ))
    return pairs


def _package_has_category(package: dict, category: str) -> bool:
    """
    Check whether any nested activity in the package matches the given
    category. Used as a client-side fallback when Swabi's server-side
    category endpoint returns 0 results (which can happen when the
    endpoint uses a different category taxonomy than the activity list).
    """
    category_lower = category.lower()
    for pa in package.get("packageActivities", []) or []:
        activity = pa.get("activity") or {}
        if (activity.get("activityCategory") or "").lower() == category_lower:
            return True
    return False


def _package_duration_days(package: dict):
    try:
        return int(package.get("noOfDays"))
    except (TypeError, ValueError):
        return None


async def recommend_packages(
    category:   str   = None,
    state:      str   = None,
    country:    str   = None,
    max_budget: float = None,
    duration:   int   = None,
    limit:      int   = TOP_N_PACKAGES,
):
    """
    Filter packages by category (server-side first, client-side fallback),
    then narrow by location, budget, and duration.

    Category fallback: Swabi's /get_package_list_by_category endpoint uses
    its own taxonomy that may differ from the activity category names. If
    the server-side call returns 0 packages but a category was given, we
    fall back to all packages and filter client-side by matching the category
    against each package's nested activity categories. This ensures queries
    like "Adventure packages in Uttarakhand" still find packages whose
    activities are tagged Adventure even if the server-side endpoint misses.

    `limit` caps returned results. Pass limit=None internally when you need
    the full set (e.g. for itinerary scheduling).
    """
    raw      = await search_packages(category)
    packages = (raw.get("data") or {}).get("content", [])

    # Server-side category returned nothing — fall back to client-side filter
    if category and len(packages) == 0:
        all_raw  = await get_all_packages()
        packages = (all_raw.get("data") or {}).get("content", [])
        # Filter client-side by nested activity category
        packages = [
            p for p in packages
            if _package_has_category(p, category)
        ]

    results = []
    for package in packages:

        if country or state:
            locations = _package_locations(package)
            if country and not any(lc == country.lower() for lc, _ in locations):
                continue
            if state and not any(ls == state.lower() for _, ls in locations):
                continue

        if max_budget is not None:
            try:
                price = float(package.get("totalPrice"))
            except (TypeError, ValueError):
                price = None
            if price is None or price > max_budget:
                continue

        if duration is not None:
            days = _package_duration_days(package)
            if days is None or days != duration:
                continue

        results.append(package)

    if limit is not None:
        return results[:limit]
    return results