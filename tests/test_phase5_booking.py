"""
Tests for Phase 5 (scoped: prepare-to-book, never place-the-booking).

The agent's job stops right before the user taps "Book Package" in the
real app — it never calls a booking-creation write endpoint at all.
These tests verify that property directly: prepare_package_booking /
prepare_activity_booking only ever make read (GET) calls, surface the
right vendor-scoped offer, and refuse to hand back a "ready_to_book"
summary for a blacked-out date.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("GROQ_API_KEY", "dummy")
os.environ.setdefault("GROQ_MODEL", "dummy")
os.environ.setdefault("SWABI_API_BASE", "https://example.com")

import asyncio

import app.tools.booking_tools as booking_tools

# --- Sample data ---

PACKAGE_OK = {
    "data": {
        "packageId": 4,
        "packageName": "Rishikesh Adventure",
        "totalPrice": 6000,
        "currency": "INR",
        "vendorId": 9,
        "packageActivities": [
            {"activity": {"activityName": "River Rafting", "weeklyOff": ["Sunday"], "activityReligiousOffDates": []}},
        ],
    }
}

ACTIVITY_OK = {
    "activityId": 10,
    "activityName": "River Rafting",
    "activityPrice": 1500,
    "currency": "INR",
    "vendorId": 9,
    "weeklyOff": ["Sunday"],
    "activityReligiousOffDates": [],
}

VENDOR_OFFERS = [
    {
        "offerCode": "PP6CAW", "offerName": "Package Coupon offer",
        "discountPercentage": 15.0, "minimumBookingAmount": 1000.0,
        "maxDiscountAmount": 1100.0,
    }
]


class _Calls:
    """Records every swabi_client.get call so tests can assert no write
    call is ever attempted and the right read calls happen."""
    get = []


def _reset():
    _Calls.get = []


async def _fake_get(self, endpoint):
    _Calls.get.append(endpoint)
    if "get_available_offer_by_vendor" in endpoint:
        return {"data": VENDOR_OFFERS}
    if "get_available_offer" in endpoint:
        return {"data": []}
    raise AssertionError(f"unexpected GET call: {endpoint}")


def _check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


async def main():
    failures = []

    # Patch the data-fetch layer as bound into booking_tools' own
    # namespace (it does `from x import y`, so patching the source
    # module after that import wouldn't affect this reference).
    booking_tools.get_package_by_id = lambda package_id: asyncio.sleep(0, result=PACKAGE_OK)
    booking_tools.get_activity_by_id = lambda activity_id: asyncio.sleep(0, result=ACTIVITY_OK)

    from app.services.swabi_client import SwabiClient
    original_get = SwabiClient.get
    original_post_authed = getattr(SwabiClient, "post_authed", None)
    SwabiClient.get = _fake_get

    async def _fail_if_called(self, *a, **kw):
        raise AssertionError("post_authed was called — the agent must never write a booking")

    if original_post_authed is not None:
        SwabiClient.post_authed = _fail_if_called

    try:
        # --- vendorId is correctly extracted from the package ---
        _reset()
        result = await booking_tools.prepare_package_booking(
            package_id=4, date_str="08-06-2026", num_people=2,  # Monday, not blacked out
        )
        if not _check(
            "prepare_package_booking returns ready_to_book with correct total",
            result["status"] == "ready_to_book" and result["estimated_total"] == 6000 * 2,
        ):
            failures.append("ready_to_book / total")

        if not _check(
            "vendor-scoped offer endpoint was called with the package's vendorId (9)",
            any("vendorId=9" in c for c in _Calls.get),
        ):
            failures.append("vendor offer lookup")

        if not _check(
            "applicable offer surfaced with the right code",
            result["applicable_offers"]
            and result["applicable_offers"][0]["offerCode"] == "PP6CAW",
        ):
            failures.append("offer surfaced")

        # --- Blackout date blocks preparation entirely ---
        _reset()
        result = await booking_tools.prepare_package_booking(
            package_id=4, date_str="07-06-2026", num_people=1,  # a Sunday -> River Rafting weeklyOff
        )
        if not _check(
            "Sunday blackout returns unavailable, not ready_to_book",
            result["status"] == "unavailable",
        ):
            failures.append("blackout blocks prepare")

        if not _check(
            "no offer lookup happens for an unavailable date",
            not _Calls.get,
        ):
            failures.append("no offer lookup on unavailable")

        # --- Same for activity booking ---
        _reset()
        result = await booking_tools.prepare_activity_booking(
            activity_id=10, date_str="08-06-2026", num_people=1,
        )
        if not _check(
            "prepare_activity_booking returns ready_to_book",
            result["status"] == "ready_to_book" and result["estimated_total"] == 1500,
        ):
            failures.append("activity ready_to_book")

        if not _check(
            "next_step tells the user to complete booking themselves",
            "app/website" in result.get("next_step", ""),
        ):
            failures.append("next_step wording")

    finally:
        SwabiClient.get = original_get
        if original_post_authed is not None:
            SwabiClient.post_authed = original_post_authed

    print()
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print(f" - {f}")
        sys.exit(1)

    print("ALL PHASE 5 (PREPARE-TO-BOOK) CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())