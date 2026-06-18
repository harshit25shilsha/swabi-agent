from fastapi import APIRouter, Path, Query

from app.tools.package_tools import get_package_by_id, recommend_packages


router = APIRouter(
    prefix="/packages",
    tags=["Packages"]
)


@router.get(
    "/{package_id}",
    summary="Get package details",
    description=(
        "Fetch full package information by package ID. Use this after selecting "
        "a package from search results. Example package_id: 4."
    )
)
async def package_detail(
    package_id: int = Path(
        ...,
        description="Unique Swabi package ID.",
        examples=[4]
    )
):
    return await get_package_by_id(package_id)


@router.get(
    "/",
    summary="Search Swabi packages",
    description=(
        "Search Swabi travel packages by category, destination (country/state), "
        "maximum budget, and/or trip duration in days. All filters are optional "
        "and combine together. Note: country/state are matched against the "
        "package's underlying activities, since packages themselves don't carry "
        "a reliable top-level location field. "
        "Example: category=Adventure, state=Uttarakhand, max_budget=8500, duration=5."
    )
)
async def package_search(
    category: str = Query(
        None,
        description="Package category name used by Swabi package search.",
        examples=["Adventure"]
    ),
    country: str = Query(
        None,
        description="Country filter, matched against the package's activities.",
        examples=["India"]
    ),
    state: str = Query(
        None,
        description="State filter, matched against the package's activities.",
        examples=["Uttarakhand"]
    ),
    max_budget: float = Query(
        None,
        description="Maximum total package price.",
        examples=[8500]
    ),
    duration: int = Query(
        None,
        description="Exact trip duration in days (matches noOfDays).",
        examples=[5]
    )
):
    return await recommend_packages(
        category=category,
        country=country,
        state=state,
        max_budget=max_budget,
        duration=duration
    )
