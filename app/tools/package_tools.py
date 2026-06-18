from app.services.swabi_client import swabi_client


async def get_package_by_id(
    package_id: int
):
    return await swabi_client.get(
        f"/package/get_package_by_id?packageId={package_id}"
    )


async def get_all_packages():
    """
    Fetch every active package across all vendors, unfiltered.
    Used as the base list when no category is given, or as the
    source list that recommend_packages further narrows down.
    """
    return await swabi_client.get(
        "/package/get_package_list_all_vendors"
        "?pageNumber=-1&pageSize=-1&packageStatus=ALL&search=&days=&price="
    )


async def search_packages(
    category: str = None
):
    """
    Search packages by category using Swabi's category endpoint.
    If no category is given, falls back to all active packages
    across all vendors instead of refusing the request, since
    location/budget/duration-only queries are valid too.
    """

    if not category:
        return await get_all_packages()

    return await swabi_client.get(
        f"/package/get_package_list_by_category?categoryName={category}&pageNumber=-1&pageSize=-1"
    )


def _package_locations(package: dict):
    """
    Packages don't reliably carry a usable top-level country/state:
    in the sample data every package's top-level "state" is blank and
    "country" is just "India" for all of them, so it can't discriminate
    between, say, an Uttarakhand package and a Goa package.

    The real location signal lives on each nested
    packageActivities[].activity, which has its own country/state.
    This returns the set of (country, state) pairs actually visited
    by the package's activities, so we can filter on real geography.
    """

    pairs = set()

    for pa in package.get("packageActivities", []) or []:
        activity = pa.get("activity") or {}
        pairs.add((
            (activity.get("country") or "").lower(),
            (activity.get("state") or "").lower()
        ))

    return pairs


def _package_duration_days(package: dict):
    """
    noOfDays is shipped as a string in the Swabi schema (e.g. "5"),
    so we coerce it defensively rather than assuming int.
    """

    try:
        return int(package.get("noOfDays"))
    except (TypeError, ValueError):
        return None


async def recommend_packages(
    category=None,
    state=None,
    country=None,
    max_budget=None,
    duration=None
):
    """
    Recommend packages filtered by category (server-side, via Swabi's
    category endpoint) and then narrowed client-side by destination
    (country/state, matched against the package's nested activities),
    budget (totalPrice <= max_budget), and trip length (noOfDays).
    """

    raw = await search_packages(category)

    # search_packages / get_all_packages return the raw Swabi envelope;
    # the package list itself lives at data.content for both endpoints.
    packages = (raw.get("data") or {}).get("content", [])

    results = []

    for package in packages:

        if country or state:
            locations = _package_locations(package)

            if country and not any(
                loc_country == country.lower()
                for loc_country, _ in locations
            ):
                continue

            if state and not any(
                loc_state == state.lower()
                for _, loc_state in locations
            ):
                continue

        if max_budget is not None:
            price = package.get("totalPrice")

            try:
                price = float(price)
            except (TypeError, ValueError):
                price = None

            if price is None or price > max_budget:
                continue

        if duration is not None:
            days = _package_duration_days(package)

            if days is None or days != duration:
                continue

        results.append(package)

    return results