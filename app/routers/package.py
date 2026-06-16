from fastapi import APIRouter, Path, Query

from app.tools.package_tools import get_package_by_id,search_packages


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
        "Search Swabi travel packages by category. "
        "Try category=Adventure or category=Religious & Pilgrim Tours."
    )
)
async def package_search(
    category: str = Query(
        ...,
        description="Package category name used by Swabi package search.",
        examples=["Adventure"]
    )
):
    return await search_packages(category)
