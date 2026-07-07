# import json
# from typing import Annotated, Optional, Union

# from langchain.tools import tool
# from langgraph.prebuilt import InjectedState

# from app.graph.state import AgentState
# from app.tools.activity_tools import (
#     search_activities,
#     get_activity_categories,
# )
# from app.tools.package_tools import (
#     search_packages,
#     get_package_by_id,
# )
# from app.tools.recommendation_tools import (
#     recommend_trip,
#     personalized_recommend_trip,
#     build_trip_itinerary,
# )
# from app.tools.user_tools import get_user_profile
# from app.tools.booking_tools import (
#     check_package_availability,
#     check_activity_availability,
#     prepare_package_booking,
#     prepare_activity_booking,
#     get_available_offers,
# )
# from app.tools.member_tools import (
#     get_countries,
#     get_states_for_country,
#     get_user_by_id,
# )
# from app.core.token_budget import (
#     summarize_activity,
#     summarize_package,
#     slim_profile,
#     TOP_N_ACTIVITIES,
#     TOP_N_PACKAGES,
# )


# def _to_float(value) -> Optional[float]:
#     """
#     Coerce LLM-supplied price/budget values to float.

#     Groq sometimes generates tool arguments as strings even when the schema
#     says float (e.g. max_price="3000" instead of 3000). This causes a 400
#     tool_use_failed error. Coercing here means the tool always receives a
#     proper float regardless of what the LLM emitted.
#     """
#     if value is None:
#         return None
#     try:
#         return float(value)
#     except (TypeError, ValueError):
#         return None


# def _to_int(value) -> Optional[int]:
#     """Same coercion for integer fields (duration, package_id, user_id)."""
#     if value is None:
#         return None
#     try:
#         return int(value)
#     except (TypeError, ValueError):
#         return None


# def _parse_members_arg(members) -> Optional[list]:
#     """
#     Groq/Llama tool-calling frequently serializes nested array arguments
#     as a JSON-encoded string rather than a real array (observed with
#     llama-3.3-70b-versatile on add_members_tool's `members` param) — the
#     Groq API then rejects a strict `array` schema outright with a 400
#     before this code even runs. Accepting `members` as a string and
#     parsing it here, rather than declaring it as `list`, sidesteps that
#     validation failure entirely. Also tolerates an already-parsed list
#     for models that do send a real array, and a single dict.
#     Returns [] for empty/None input, or None if parsing genuinely fails.
#     """
#     if members is None or members == "":
#         return []
#     if isinstance(members, list):
#         return members
#     if isinstance(members, dict):
#         return [members]
#     if isinstance(members, str):
#         try:
#             parsed = json.loads(members)
#         except (TypeError, ValueError):
#             return None
#         if isinstance(parsed, dict):
#             return [parsed]
#         if isinstance(parsed, list):
#             return parsed
#         return None
#     return None


# # Activity tools 

# @tool
# async def activity_search_tool(
#     country:   Optional[str]            = None,
#     state:     Optional[str]            = None,
#     city:      Optional[str]            = None,
#     category:  Optional[str]            = None,
#     max_price: Optional[Union[float, str]] = None,
# ):
#     """Search activities by location/category/max price. Returns top results.
#     Call activity_category_list_tool first when the exact category name is
#     uncertain. Use trip_recommendation_tool for multi-constraint queries."""

#     results = await search_activities(
#         country=country,
#         state=state,
#         city=city,
#         category=category,
#         max_price=_to_float(max_price),
#     )
#     capped = results[:TOP_N_ACTIVITIES]
#     lines  = [summarize_activity(a) for a in capped]
#     if len(results) > TOP_N_ACTIVITIES:
#         lines.append(f"... +{len(results) - TOP_N_ACTIVITIES} more (refine filters to narrow)")
#     return "\n".join(lines) or "No activities found."


# @tool
# async def activity_category_list_tool():
#     """Return valid Swabi category names. Call before any category-filtered
#     search when unsure of exact spelling."""

#     result = await get_activity_categories()
#     return json.dumps(result, default=str)


# #  Package tools 

# @tool
# async def package_search_tool(category: str):
#     """Search packages by category. Use trip_recommendation_tool when
#     location, budget, or duration is also given."""

#     result   = await search_packages(category=category)
#     packages = (result.get("data") or {}).get("content", [])
#     capped   = packages[:TOP_N_PACKAGES]
#     lines    = [summarize_package(p) for p in capped]
#     if len(packages) > TOP_N_PACKAGES:
#         lines.append(f"... +{len(packages) - TOP_N_PACKAGES} more packages")
#     return "\n\n".join(lines) or "No packages found."


# @tool
# async def package_detail_tool(package_id: Union[int, str]):
#     """Full details for one package by numeric ID. Use after the user picks
#     a specific package from search results."""

#     result  = await get_package_by_id(_to_int(package_id))
#     package = result.get("data") or result
#     return summarize_package(package, detail=True)


# #  Recommendation tools 

# @tool
# async def trip_recommendation_tool(
#     destination: Optional[str]            = None,
#     category:    Optional[str]            = None,
#     country:     Optional[str]            = None,
#     state:       Optional[str]            = None,
#     max_budget:  Optional[Union[float, str]] = None,
#     duration:    Optional[Union[int, str]]   = None,
# ):
#     """Recommend activities + packages filtered by destination, category,
#     budget, and/or days. Use for multi-constraint trip queries.
#     Use itinerary_planner_tool when the user wants a day-by-day plan."""

#     result = await recommend_trip(
#         destination=destination,
#         category=category,
#         country=country,
#         state=state,
#         max_budget=_to_float(max_budget),
#         duration=_to_int(duration),
#     )

#     acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
#     pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
#     act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
#     pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

#     return (
#         f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
#         f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
#     )


# @tool
# async def personalized_trip_recommendation_tool(
#     user_id:     Union[int, str],
#     destination: Optional[str]            = None,
#     category:    Optional[str]            = None,
#     country:     Optional[str]            = None,
#     state:       Optional[str]            = None,
#     max_budget:  Optional[Union[float, str]] = None,
#     duration:    Optional[Union[int, str]]   = None,
# ):
#     """Like trip_recommendation_tool but fills missing destination/category
#     from the user's booking history and preferences. Use when user_id is
#     known and the request is open-ended. Explicit args override profile."""

#     result = await personalized_recommend_trip(
#         user_id=_to_int(user_id),
#         destination=destination,
#         category=category,
#         country=country,
#         state=state,
#         max_budget=_to_float(max_budget),
#         duration=_to_int(duration),
#     )

#     acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
#     pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
#     filters   = result.get("resolved_filters", {})

#     act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
#     pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

#     return (
#         f"RESOLVED_FILTERS: {json.dumps(filters)}\n\n"
#         f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
#         f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
#     )


# #  Itinerary tool 

# @tool
# async def itinerary_planner_tool(
#     destination: Optional[str]            = None,
#     category:    Optional[str]            = None,
#     country:     Optional[str]            = None,
#     state:       Optional[str]            = None,
#     max_budget:  Optional[Union[float, str]] = None,
#     duration:    Optional[Union[int, str]]   = None,
#     start_date:  Optional[str]            = None,
#     user_id:     Optional[Union[int, str]]   = None,
# ):
#     """Build a day-by-day itinerary scheduling activities onto specific days,
#     respecting closures and time overlaps. Use for PLAN/SCHEDULE requests
#     ('plan my trip', 'day by day', 'build an itinerary').
#     start_date format: DD-MM-YYYY. duration defaults to 3."""

#     result = await build_trip_itinerary(
#         destination=destination,
#         category=category,
#         country=country,
#         state=state,
#         max_budget=_to_float(max_budget),
#         duration=_to_int(duration),
#         start_date=start_date,
#         user_id=_to_int(user_id),
#     )

#     lines = []

#     if result.get("duration_was_defaulted"):
#         lines.append(
#             f"NOTE: duration not specified — defaulted to "
#             f"{result.get('duration_used')} days."
#         )

#     for day in result.get("itinerary", []):
#         day_acts  = day.get("activities", [])
#         act_lines = "\n  ".join(
#             summarize_activity(a) for a in day_acts
#         ) or "no activities scheduled"
#         lines.append(
#             f"Day {day['day_number']} ({day['weekday']}, {day['date']}) "
#             f"— {day['total_hours']}h:\n  {act_lines}"
#         )

#     unscheduled = result.get("unscheduled_activities", [])
#     if unscheduled:
#         names = ", ".join(a.get("activityName", "?") for a in unscheduled[:5])
#         extra = f" (+{len(unscheduled) - 5} more)" if len(unscheduled) > 5 else ""
#         lines.append(f"UNSCHEDULED ({len(unscheduled)}): {names}{extra}")

#     pkgs = result.get("packages", [])[:TOP_N_PACKAGES]
#     if pkgs:
#         pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs)
#         lines.append(f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}")

#     return "\n\n".join(lines) or "No itinerary could be built."


# # User profile tool 

# @tool
# async def user_profile_tool(user_id: Union[int, str]):
#     """Return a user's travel preferences and booking history summary.
#     Use when the user asks what you know about them, or to explain a
#     personalized recommendation."""

#     result = await get_user_profile(_to_int(user_id))
#     return json.dumps(slim_profile(result), default=str)


# #  Booking tools (Phase 5) 

# def _require_auth(state: AgentState):
#     """
#     Return (auth_user, None) if this session is authenticated, else
#     (None, error_message). auth_user.token/.user_id come from the
#     verified JWT in graph state — never from an LLM-supplied argument —
#     so a booking can never be placed against a user_id the LLM invented
#     or was tricked into using.
#     """
#     auth_user = state.get("auth_user")
#     if not auth_user:
#         return None, (
#             "This session isn't authenticated. Log in via POST /auth/login "
#             "and start a new session with the returned token to book."
#         )
#     return auth_user, None


# @tool
# async def check_availability_tool(
#     date: str,
#     state: Annotated[AgentState, InjectedState],
#     package_id: Optional[Union[int, str]] = None,
#     activity_id: Optional[Union[int, str]] = None,
# ):
#     """Check whether a package or activity is open on a given date
#     (format DD-MM-YYYY). Pass exactly one of package_id or activity_id.
#     Always call this before create_booking_tool."""

#     if package_id:
#         result = await check_package_availability(_to_int(package_id), date)
#     elif activity_id:
#         result = await check_activity_availability(_to_int(activity_id), date)
#     else:
#         return "Provide either package_id or activity_id."

#     return json.dumps(result, default=str)


# @tool
# async def prepare_booking_tool(
#     date: str,
#     num_people: Union[int, str],
#     state: Annotated[AgentState, InjectedState],
#     package_id: Optional[Union[int, str]] = None,
#     activity_id: Optional[Union[int, str]] = None,
# ):
#     """Get everything the user needs to book a package or activity —
#     availability, price, and any offer/coupon that applies — the same
#     information the app shows right before its own "Book Package"
#     button. Pass exactly one of package_id or activity_id.

#     This does NOT place a booking. The agent's role stops here; tell the
#     user to complete the booking themselves in the Swabi app/website."""

#     auth_user, error = _require_auth(state)
#     if error:
#         return error

#     if not package_id and not activity_id:
#         return "Provide either package_id or activity_id."

#     if package_id:
#         result = await prepare_package_booking(
#             package_id=_to_int(package_id),
#             date_str=date,
#             num_people=_to_int(num_people) or 1,
#         )
#     else:
#         result = await prepare_activity_booking(
#             activity_id=_to_int(activity_id),
#             date_str=date,
#             num_people=_to_int(num_people) or 1,
#         )

#     return json.dumps(result, default=str)


# @tool
# async def available_offers_tool(date: str, offer_type: str = "PACKAGE_BOOKING"):
#     """Look up active discount/coupon offers for a booking date (format
#     DD-MM-YYYY). offer_type is usually PACKAGE_BOOKING. Use when the user
#     asks about discounts/coupons, or proactively mention one before
#     confirming a booking if it would apply."""

#     offers = await get_available_offers(date, offer_type)
#     if not offers:
#         return "No active offers for that date."

#     lines = []
#     for o in offers:
#         lines.append(
#             f"code={o.get('offerCode')} | {o.get('offerName')} | "
#             f"{o.get('discountPercentage')}% off | "
#             f"min booking {o.get('minimumBookingAmount')} {o.get('minCurrency')} | "
#             f"max discount {o.get('maxDiscountAmount')} {o.get('maxCurrency')} | "
#             f"valid {o.get('startDate')} to {o.get('endDate')}"
#         )
#     return "\n".join(lines)


# #  Add Members (Phase 5 — traveler details, still no write call) 

# @tool
# async def country_list_tool():
#     """List valid country names, for the Add Members step. Use if unsure
#     of exact spelling before validating a traveler's country."""

#     countries = await get_countries()
#     names = sorted(c["country"] for c in countries)
#     return ", ".join(names)


# @tool
# async def country_states_tool(country: str):
#     """List valid state/province names for a given country, for the
#     Add Members step."""

#     states = await get_states_for_country(country)
#     if not states:
#         return (
#             f"No states on file for '{country}' — it may not need one, "
#             f"or check the spelling with country_list_tool."
#         )
#     return ", ".join(states)


# @tool
# async def add_members_tool(
#     num_people: Union[int, str],
#     state: Annotated[AgentState, InjectedState],
#     members: Optional[str] = None,
# ):
#     """Collect and validate traveler details for a booking — the Add
#     Members step right after the user has seen the price/offer summary
#     from prepare_booking_tool, and right before they complete the
#     booking themselves.

#     members: a JSON array string, one object per traveler, e.g.
#     '[{"name": "Ritik Kumar", "country": "India", "state": "Uttarakhand",
#     "mobile": "9876543210"}]'. Always pass it as a JSON string, not a
#     native list. country/state are validated against Swabi's live
#     lists — invalid ones are flagged, never silently accepted or
#     guessed. If fewer members are given than num_people, the first
#     (primary) traveler is auto-filled from the logged-in user's own
#     Swabi account.

#     This does not submit anything — it only prepares and validates the
#     traveler list for the user to review before they book."""

#     auth_user, error = _require_auth(state)
#     if error:
#         return error

#     parsed_members = _parse_members_arg(members)
#     if parsed_members is None:
#         return (
#             "Couldn't read the traveler list — pass members as a JSON "
#             'array string, e.g. \'[{"name": "...", "country": "...", '
#             '"state": "..."}]\'.'
#         )

#     n = _to_int(num_people) or max(len(parsed_members), 1)
#     members_list = parsed_members

#     if len(members_list) < n:
#         try:
#             profile = await get_user_by_id(auth_user.user_id, auth_user.token)
#         except Exception:
#             profile = {}
#         if profile:
#             primary = {
#                 "name": (
#                     f"{profile.get('firstName', '')} {profile.get('lastName', '')}"
#                 ).strip() or auth_user.first_name,
#                 "country": profile.get("country"),
#                 "state":   profile.get("state"),
#                 "mobile":  profile.get("mobile"),
#             }
#             members_list = [primary] + members_list

#     validated = []
#     warnings = []
#     for i, m in enumerate(members_list[:n], start=1):
#         entry = {
#             "name":    m.get("name") or f"Traveler {i}",
#             "country": m.get("country"),
#             "state":   m.get("state"),
#             "mobile":  m.get("mobile"),
#         }
#         if entry["country"]:
#             states = await get_states_for_country(entry["country"])
#             if entry["state"] and states and entry["state"] not in states:
#                 warnings.append(
#                     f"Traveler {i}: '{entry['state']}' isn't a recognized "
#                     f"state for {entry['country']} — please confirm."
#                 )
#         elif entry["state"]:
#             warnings.append(f"Traveler {i}: state given without a country.")
#         validated.append(entry)

#     still_needed = max(n - len(validated), 0)

#     return json.dumps({
#         "members":          validated,
#         "members_provided": len(validated),
#         "members_needed":   n,
#         "still_needed":     still_needed,
#         "warnings":         warnings,
#         "next_step": (
#             "Once all travelers are added and any warnings are resolved, "
#             "complete the booking yourself in the Swabi app/website — "
#             "the agent doesn't submit it."
#         ),
#     }, default=str)


# #  Tool registry 

# tools = [
#     activity_search_tool,
#     activity_category_list_tool,
#     package_search_tool,
#     package_detail_tool,
#     trip_recommendation_tool,
#     personalized_trip_recommendation_tool,
#     itinerary_planner_tool,
#     user_profile_tool,
#     check_availability_tool,
#     prepare_booking_tool,
#     available_offers_tool,
#     country_list_tool,
#     country_states_tool,
#     add_members_tool,
# ]

import json
from typing import Annotated, Optional, Union

from langchain.tools import tool
from langgraph.prebuilt import InjectedState

from app.graph.state import AgentState
from app.tools.activity_tools import (
    search_activities,
    get_activity_categories,
)
from app.tools.package_tools import (
    search_packages,
    get_package_by_id,
)
from app.tools.recommendation_tools import (
    recommend_trip,
    personalized_recommend_trip,
    build_trip_itinerary,
)
from app.tools.user_tools import get_user_profile, get_user_bookings
from app.tools.booking_tools import (
    check_package_availability,
    check_activity_availability,
    prepare_package_booking,
    prepare_activity_booking,
    get_available_offers,
)
from app.tools.member_tools import (
    get_countries,
    get_states_for_country,
    get_user_by_id,
)
from app.core.token_budget import (
    summarize_activity,
    summarize_package,
    summarize_booking,
    slim_profile,
    TOP_N_ACTIVITIES,
    TOP_N_PACKAGES,
)


def _to_float(value) -> Optional[float]:
    """
    Coerce LLM-supplied price/budget values to float.

    Groq sometimes generates tool arguments as strings even when the schema
    says float (e.g. max_price="3000" instead of 3000). This causes a 400
    tool_use_failed error. Coercing here means the tool always receives a
    proper float regardless of what the LLM emitted.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    """Same coercion for integer fields (duration, package_id, user_id)."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_members_arg(members) -> Optional[list]:
    """
    Groq/Llama tool-calling frequently serializes nested array arguments
    as a JSON-encoded string rather than a real array (observed with
    llama-3.3-70b-versatile on add_members_tool's `members` param) — the
    Groq API then rejects a strict `array` schema outright with a 400
    before this code even runs. Accepting `members` as a string and
    parsing it here, rather than declaring it as `list`, sidesteps that
    validation failure entirely. Also tolerates an already-parsed list
    for models that do send a real array, and a single dict.
    Returns [] for empty/None input, or None if parsing genuinely fails.
    """
    if members is None or members == "":
        return []
    if isinstance(members, list):
        return members
    if isinstance(members, dict):
        return [members]
    if isinstance(members, str):
        try:
            parsed = json.loads(members)
        except (TypeError, ValueError):
            return None
        if isinstance(parsed, dict):
            return [parsed]
        if isinstance(parsed, list):
            return parsed
        return None
    return None


# Activity tools 

@tool
async def activity_search_tool(
    country:   Optional[str]            = None,
    state:     Optional[str]            = None,
    city:      Optional[str]            = None,
    category:  Optional[str]            = None,
    max_price: Optional[Union[float, str]] = None,
):
    """Search activities by location/category/max price. Returns top results.
    Call activity_category_list_tool first when the exact category name is
    uncertain. Use trip_recommendation_tool for multi-constraint queries."""

    results = await search_activities(
        country=country,
        state=state,
        city=city,
        category=category,
        max_price=_to_float(max_price),
    )
    capped = results[:TOP_N_ACTIVITIES]
    lines  = [summarize_activity(a) for a in capped]
    if len(results) > TOP_N_ACTIVITIES:
        lines.append(f"... +{len(results) - TOP_N_ACTIVITIES} more (refine filters to narrow)")
    return "\n".join(lines) or "No activities found."


@tool
async def activity_category_list_tool():
    """Return valid Swabi category names. Call before any category-filtered
    search when unsure of exact spelling."""

    result = await get_activity_categories()
    return json.dumps(result, default=str)


#  Package tools 

@tool
async def package_search_tool(category: str):
    """Search packages by category. Use trip_recommendation_tool when
    location, budget, or duration is also given."""

    result   = await search_packages(category=category)
    packages = (result.get("data") or {}).get("content", [])
    capped   = packages[:TOP_N_PACKAGES]
    lines    = [summarize_package(p) for p in capped]
    if len(packages) > TOP_N_PACKAGES:
        lines.append(f"... +{len(packages) - TOP_N_PACKAGES} more packages")
    return "\n\n".join(lines) or "No packages found."


@tool
async def package_detail_tool(package_id: Union[int, str]):
    """Full details for one package by numeric ID. Use after the user picks
    a specific package from search results."""

    result  = await get_package_by_id(_to_int(package_id))
    package = result.get("data") or result
    return summarize_package(package, detail=True)


#  Recommendation tools 

@tool
async def trip_recommendation_tool(
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
):
    """Recommend activities + packages filtered by destination, category,
    budget, and/or days. Use for multi-constraint trip queries.
    Use itinerary_planner_tool when the user wants a day-by-day plan."""

    result = await recommend_trip(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
    )

    acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
    pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
    act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
    pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

    return (
        f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
        f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
    )


@tool
async def personalized_trip_recommendation_tool(
    user_id:     Union[int, str],
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
):
    """Like trip_recommendation_tool but fills missing destination/category
    from the user's booking history and preferences. Use when user_id is
    known and the request is open-ended. Explicit args override profile."""

    result = await personalized_recommend_trip(
        user_id=_to_int(user_id),
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
    )

    acts      = result.get("activities", [])[:TOP_N_ACTIVITIES]
    pkgs      = result.get("packages",   [])[:TOP_N_PACKAGES]
    filters   = result.get("resolved_filters", {})

    act_lines = "\n".join(summarize_activity(a) for a in acts) or "none"
    pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs) or "none"

    return (
        f"RESOLVED_FILTERS: {json.dumps(filters)}\n\n"
        f"ACTIVITIES (top {len(acts)}):\n{act_lines}\n\n"
        f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}"
    )


#  Itinerary tool 

@tool
async def itinerary_planner_tool(
    destination: Optional[str]            = None,
    category:    Optional[str]            = None,
    country:     Optional[str]            = None,
    state:       Optional[str]            = None,
    max_budget:  Optional[Union[float, str]] = None,
    duration:    Optional[Union[int, str]]   = None,
    start_date:  Optional[str]            = None,
    user_id:     Optional[Union[int, str]]   = None,
):
    """Build a day-by-day itinerary scheduling activities onto specific days,
    respecting closures and time overlaps. Use for PLAN/SCHEDULE requests
    ('plan my trip', 'day by day', 'build an itinerary').
    start_date format: DD-MM-YYYY. duration defaults to 3."""

    result = await build_trip_itinerary(
        destination=destination,
        category=category,
        country=country,
        state=state,
        max_budget=_to_float(max_budget),
        duration=_to_int(duration),
        start_date=start_date,
        user_id=_to_int(user_id),
    )

    lines = []

    if result.get("duration_was_defaulted"):
        lines.append(
            f"NOTE: duration not specified — defaulted to "
            f"{result.get('duration_used')} days."
        )

    for day in result.get("itinerary", []):
        day_acts  = day.get("activities", [])
        act_lines = "\n  ".join(
            summarize_activity(a) for a in day_acts
        ) or "no activities scheduled"
        lines.append(
            f"Day {day['day_number']} ({day['weekday']}, {day['date']}) "
            f"— {day['total_hours']}h:\n  {act_lines}"
        )

    unscheduled = result.get("unscheduled_activities", [])
    if unscheduled:
        names = ", ".join(a.get("activityName", "?") for a in unscheduled[:5])
        extra = f" (+{len(unscheduled) - 5} more)" if len(unscheduled) > 5 else ""
        lines.append(f"UNSCHEDULED ({len(unscheduled)}): {names}{extra}")

    pkgs = result.get("packages", [])[:TOP_N_PACKAGES]
    if pkgs:
        pkg_lines = "\n\n".join(summarize_package(p) for p in pkgs)
        lines.append(f"PACKAGES (top {len(pkgs)}):\n{pkg_lines}")

    return "\n\n".join(lines) or "No itinerary could be built."


# User profile tool 

@tool
async def user_profile_tool(user_id: Union[int, str]):
    """Return a user's travel preferences and booking history summary.
    Use when the user asks what you know about them, or to explain a
    personalized recommendation."""

    result = await get_user_profile(_to_int(user_id))
    return json.dumps(slim_profile(result), default=str)


#  Booking tools (Phase 5) 

def _require_auth(state: AgentState):
    """
    Return (auth_user, None) if this session is authenticated, else
    (None, error_message). auth_user.token/.user_id come from the
    verified JWT in graph state — never from an LLM-supplied argument —
    so a booking can never be placed against a user_id the LLM invented
    or was tricked into using.
    """
    auth_user = state.get("auth_user")
    if not auth_user:
        return None, (
            "This session isn't authenticated. Log in via POST /auth/login "
            "and start a new session with the returned token to book."
        )
    return auth_user, None


@tool
async def check_availability_tool(
    date: str,
    state: Annotated[AgentState, InjectedState],
    package_id: Optional[Union[int, str]] = None,
    activity_id: Optional[Union[int, str]] = None,
):
    """Check whether a package or activity is open on a given date
    (format DD-MM-YYYY). Pass exactly one of package_id or activity_id.
    Always call this before prepare_booking_tool."""

    if package_id:
        result = await check_package_availability(_to_int(package_id), date)
    elif activity_id:
        result = await check_activity_availability(_to_int(activity_id), date)
    else:
        return "Provide either package_id or activity_id."

    return json.dumps(result, default=str)


@tool
async def prepare_booking_tool(
    date: str,
    num_people: Union[int, str],
    state: Annotated[AgentState, InjectedState],
    package_id: Optional[Union[int, str]] = None,
    activity_id: Optional[Union[int, str]] = None,
):
    """Get everything the user needs to book a package or activity —
    availability, price, and any offer/coupon that applies — the same
    information the app shows right before its own "Book Package"
    button. Pass exactly one of package_id or activity_id.

    This does NOT place a booking. The agent's role stops here; tell the
    user to complete the booking themselves in the Swabi app/website."""

    auth_user, error = _require_auth(state)
    if error:
        return error

    if not package_id and not activity_id:
        return "Provide either package_id or activity_id."

    if package_id:
        result = await prepare_package_booking(
            package_id=_to_int(package_id),
            date_str=date,
            num_people=_to_int(num_people) or 1,
        )
    else:
        result = await prepare_activity_booking(
            activity_id=_to_int(activity_id),
            date_str=date,
            num_people=_to_int(num_people) or 1,
        )

    return json.dumps(result, default=str)


@tool
async def available_offers_tool(date: str, offer_type: str = "PACKAGE_BOOKING"):
    """Look up active discount/coupon offers for a booking date (format
    DD-MM-YYYY). offer_type is usually PACKAGE_BOOKING. Use when the user
    asks about discounts/coupons, or proactively mention one before
    confirming a booking if it would apply."""

    offers = await get_available_offers(date, offer_type)
    if not offers:
        return "No active offers for that date."

    lines = []
    for o in offers:
        lines.append(
            f"code={o.get('offerCode')} | {o.get('offerName')} | "
            f"{o.get('discountPercentage')}% off | "
            f"min booking {o.get('minimumBookingAmount')} {o.get('minCurrency')} | "
            f"max discount {o.get('maxDiscountAmount')} {o.get('maxCurrency')} | "
            f"valid {o.get('startDate')} to {o.get('endDate')}"
        )
    return "\n".join(lines)


#  Add Members (Phase 5 — traveler details, still no write call) 

@tool
async def country_list_tool():
    """List valid country names, for the Add Members step. Use if unsure
    of exact spelling before validating a traveler's country."""

    countries = await get_countries()
    names = sorted(c["country"] for c in countries)
    return ", ".join(names)


@tool
async def country_states_tool(country: str):
    """List valid state/province names for a given country, for the
    Add Members step."""

    states = await get_states_for_country(country)
    if not states:
        return (
            f"No states on file for '{country}' — it may not need one, "
            f"or check the spelling with country_list_tool."
        )
    return ", ".join(states)


@tool
async def add_members_tool(
    num_people: Union[int, str],
    state: Annotated[AgentState, InjectedState],
    members: Optional[str] = None,
):
    """Collect and validate traveler details for a booking — the Add
    Members step right after the user has seen the price/offer summary
    from prepare_booking_tool, and right before they complete the
    booking themselves.

    Traveler 1 is ALWAYS the logged-in user and is auto-filled from
    their own Swabi account automatically — never invent, guess, or ask
    for their name/country/state, and never include them in `members`.

    members: a JSON array string of the OTHER travelers only (traveler
    2 onward), e.g. for num_people=2 this should contain exactly ONE
    entry: '[{"name": "Priya Sharma", "country": "India", "state":
    "Delhi"}]'. Always pass it as a JSON string, not a native list. If
    the user hasn't given you a later traveler's details yet, leave
    them out of `members` and ask for them — don't invent placeholders
    for anyone. country/state are validated against Swabi's live
    lists — invalid ones are flagged, never silently accepted or
    guessed.

    This does not submit anything — it only prepares and validates the
    traveler list for the user to review before they book."""

    auth_user, error = _require_auth(state)
    if error:
        return error

    parsed_members = _parse_members_arg(members)
    if parsed_members is None:
        return (
            "Couldn't read the traveler list — pass members as a JSON "
            'array string, e.g. \'[{"name": "...", "country": "...", '
            '"state": "..."}]\'.'
        )

    n = _to_int(num_people) or (len(parsed_members) + 1)

    # Traveler 1 is always the account holder, pulled from their own
    # Swabi profile — never taken from the LLM-supplied members list.
    # This is what stops the model inventing a placeholder name (seen
    # in testing: it once filled traveler 1 in as "there") when the
    # user only gave details for someone else.
    try:
        profile = await get_user_by_id(auth_user.user_id, auth_user.token)
    except Exception:
        profile = {}

    primary_name = (
        f"{profile.get('firstName', '')} {profile.get('lastName', '')}".strip()
        or f"{auth_user.first_name} {auth_user.last_name}".strip()
        or "Primary traveler (you)"
    )
    primary = {
        "name":    primary_name,
        "country": profile.get("country"),
        "state":   profile.get("state"),
        "mobile":  profile.get("mobile"),
    }

    warnings = []

    # The model is told never to include traveler 1 itself, but if it
    # does anyway, len(parsed_members) will be >= n. Blindly prepending
    # primary and truncating to n would then silently drop the LAST
    # (usually the most concretely-described, e.g. "Priya Sharma") entry
    # instead of the spurious invented one, which tends to appear first.
    # Keep the most recent (n - 1) entries instead, and say so.
    max_others = max(n - 1, 0)
    if len(parsed_members) > max_others:
        dropped = len(parsed_members) - max_others
        parsed_members = parsed_members[-max_others:] if max_others else []
        warnings.append(
            f"Got {dropped} more traveler entr{'y' if dropped == 1 else 'ies'} than "
            f"expected for {n} people (traveler 1 is always the account holder and "
            f"shouldn't be listed separately) — used the most recently described "
            f"traveler(s) and ignored the extra."
        )

    members_list = [primary] + parsed_members

    validated = []
    for i, m in enumerate(members_list[:n], start=1):
        entry = {
            "name":    m.get("name") or f"Traveler {i}",
            "country": m.get("country"),
            "state":   m.get("state"),
            "mobile":  m.get("mobile"),
        }
        if entry["country"]:
            states = await get_states_for_country(entry["country"])
            if entry["state"] and states and entry["state"] not in states:
                warnings.append(
                    f"Traveler {i}: '{entry['state']}' isn't a recognized "
                    f"state for {entry['country']} — please confirm."
                )
        elif entry["state"]:
            warnings.append(f"Traveler {i}: state given without a country.")
        validated.append(entry)

    still_needed = max(n - len(validated), 0)

    return json.dumps({
        "members":          validated,
        "members_provided": len(validated),
        "members_needed":   n,
        "still_needed":     still_needed,
        "warnings":         warnings,
        "next_step": (
            "Once all travelers are added and any warnings are resolved, "
            "complete the booking yourself in the Swabi app/website — "
            "the agent doesn't submit it."
        ),
    }, default=str)


#  Booking History (Phase 6 — read-only, closes the loop after hand-off) 

@tool
async def booking_history_tool(
    state: Annotated[AgentState, InjectedState],
    booking_status: str = "ALL",
):
    """View the logged-in user's past/current package bookings — name,
    status, date, headcount, total — so they can ask "what did I book?"
    or "is my booking confirmed?" without leaving chat.

    booking_status: one of ALL, PENDING, CONFIRMED, CANCELLED (whatever
    Swabi's own status values are) — defaults to ALL.

    Read-only. This is the ONLY thing the agent can tell the user about
    a completed booking — it cannot cancel, reschedule, retry payment,
    or change anything here. Always use the account holder's own
    identity from the verified session; there is no user_id parameter
    because this must never be called for anyone but the logged-in
    user themselves.
    """

    auth_user, error = _require_auth(state)
    if error:
        return error

    result = await get_user_bookings(auth_user.user_id, booking_status)
    bookings = (result.get("data") or {}).get("content", [])

    if not bookings:
        return f"No bookings found (status filter: {booking_status})."

    lines = [summarize_booking(b) for b in bookings]
    return "\n".join(lines)


#  Tool registry 

tools = [
    activity_search_tool,
    activity_category_list_tool,
    package_search_tool,
    package_detail_tool,
    trip_recommendation_tool,
    personalized_trip_recommendation_tool,
    itinerary_planner_tool,
    user_profile_tool,
    check_availability_tool,
    prepare_booking_tool,
    available_offers_tool,
    country_list_tool,
    country_states_tool,
    add_members_tool,
    booking_history_tool,
]