from datetime import datetime

from app.services.swabi_client import swabi_client
from app.tools.package_tools import get_package_by_id
from app.tools.activity_tools import get_activity_by_id
from app.tools.itinerary_tools import _is_activity_closed_on


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except (TypeError, ValueError):
        return None


def _safe_total(price, num_people):
    try:
        return float(price) * int(num_people)
    except (TypeError, ValueError):
        return None


def _extract_vendor_id(package_or_activity: dict):
    """
    Best-effort vendor ID lookup. Not yet confirmed which of these shapes
    Swabi actually uses — tries the plausible spots in order and returns
    the first hit. Returns None if none match, which just means offers
    lookup falls back to the non-vendor-scoped endpoint.
    """
    for key in ("vendorId", "vendor_id"):
        if package_or_activity.get(key) is not None:
            return package_or_activity[key]

    vendor = package_or_activity.get("vendor") or {}
    for key in ("vendorId", "id"):
        if vendor.get(key) is not None:
            return vendor[key]

    for pa in package_or_activity.get("packageActivities", []) or []:
        activity = pa.get("activity") or {}
        found = _extract_vendor_id(activity)
        if found is not None:
            return found

    return None


#  Availability 

async def check_package_availability(package_id: int, date_str: str) -> dict:
    """Check whether every activity in a package is open on the given date."""
    the_date = _parse_date(date_str)
    if the_date is None:
        return {
            "available": False,
            "reason": f"Could not parse date '{date_str}', expected DD-MM-YYYY.",
        }

    result = await get_package_by_id(package_id)
    package = result.get("data") or result
    if not package:
        return {"available": False, "reason": f"Package {package_id} not found."}

    closed = []
    for pa in package.get("packageActivities", []) or []:
        activity = pa.get("activity") or {}
        if _is_activity_closed_on(activity, the_date):
            closed.append(activity.get("activityName", "?"))

    if closed:
        return {
            "available": False,
            "reason": f"Closed on {date_str}: {', '.join(closed)}",
            "package_id": package_id,
        }

    return {
        "available":    True,
        "package_id":   package_id,
        "date":         date_str,
        "package_name": package.get("packageName"),
        "price":        package.get("totalPrice"),
        "currency":     package.get("currency") or "INR",
        "vendor_id":    _extract_vendor_id(package),
    }


async def check_activity_availability(activity_id: int, date_str: str) -> dict:
    the_date = _parse_date(date_str)
    if the_date is None:
        return {
            "available": False,
            "reason": f"Could not parse date '{date_str}', expected DD-MM-YYYY.",
        }

    activity = await get_activity_by_id(activity_id)
    if not activity:
        return {"available": False, "reason": f"Activity {activity_id} not found."}

    if _is_activity_closed_on(activity, the_date):
        return {
            "available": False,
            "reason": f"{activity.get('activityName')} is closed on {date_str}.",
            "activity_id": activity_id,
        }

    return {
        "available":     True,
        "activity_id":   activity_id,
        "date":          date_str,
        "activity_name": activity.get("activityName"),
        "price":         activity.get("activityPrice"),
        "currency":      activity.get("currency") or "INR",
        "vendor_id":     _extract_vendor_id(activity),
    }


#  Offers 

async def get_available_offers(date_str: str, offer_type: str = "PACKAGE_BOOKING") -> list:
    """All active offers for a date/type (not vendor-scoped)."""
    response = await swabi_client.get(
        f"/offer/get_available_offer?date={date_str}&offerType={offer_type}"
    )
    return response.get("data") or []


async def get_available_offers_by_vendor(
    vendor_id: int, date_str: str, offer_type: str = "package_booking"
) -> list:
    """Offers scoped to a specific vendor — this is what the real app
    calls right before showing the "Book Package" button."""
    response = await swabi_client.get(
        f"/offer/get_available_offer_by_vendor"
        f"?date={date_str}&offerType={offer_type}&vendorId={vendor_id}"
    )
    return response.get("data") or []


#  Prepare-to-book summary (no write call) 

async def prepare_package_booking(package_id: int, date_str: str, num_people: int) -> dict:
    """
    Everything the user needs to make the final call to book, mirroring
    what the app shows right before its own "Book Package" button:
    availability, price, and any vendor offer that applies. Never writes
    anything — booking itself happens in the app, not here.
    """
    availability = await check_package_availability(package_id, date_str)
    if not availability.get("available"):
        return {"status": "unavailable", **availability}

    vendor_id = availability.get("vendor_id")
    offers = []
    if vendor_id is not None:
        offers = await get_available_offers_by_vendor(vendor_id, date_str)
    if not offers:
        offers = await get_available_offers(date_str)

    return {
        "status":          "ready_to_book",
        "package_id":      package_id,
        "package_name":    availability.get("package_name"),
        "date":             date_str,
        "num_people":       num_people,
        "price_per_unit":   availability.get("price"),
        "currency":         availability.get("currency"),
        "estimated_total":  _safe_total(availability.get("price"), num_people),
        "applicable_offers": [
            {
                "offerCode": o.get("offerCode"),
                "offerName": o.get("offerName"),
                "discountPercentage": o.get("discountPercentage"),
                "minimumBookingAmount": o.get("minimumBookingAmount"),
                "maxDiscountAmount": o.get("maxDiscountAmount"),
            }
            for o in offers
        ],
        "next_step": (
            "Complete this booking in the Swabi app/website by tapping "
            "'Book Package' — the agent doesn't place bookings itself."
        ),
    }


async def prepare_activity_booking(activity_id: int, date_str: str, num_people: int) -> dict:
    availability = await check_activity_availability(activity_id, date_str)
    if not availability.get("available"):
        return {"status": "unavailable", **availability}

    vendor_id = availability.get("vendor_id")
    offers = []
    if vendor_id is not None:
        offers = await get_available_offers_by_vendor(
            vendor_id, date_str, offer_type="activity_booking"
        )

    return {
        "status":           "ready_to_book",
        "activity_id":      activity_id,
        "activity_name":    availability.get("activity_name"),
        "date":             date_str,
        "num_people":       num_people,
        "price_per_unit":   availability.get("price"),
        "currency":         availability.get("currency"),
        "estimated_total":  _safe_total(availability.get("price"), num_people),
        "applicable_offers": [
            {
                "offerCode": o.get("offerCode"),
                "offerName": o.get("offerName"),
                "discountPercentage": o.get("discountPercentage"),
                "minimumBookingAmount": o.get("minimumBookingAmount"),
                "maxDiscountAmount": o.get("maxDiscountAmount"),
            }
            for o in offers
        ],
        "next_step": (
            "Complete this booking in the Swabi app/website by tapping "
            "'Book Activity' — the agent doesn't place bookings itself."
        ),
    }