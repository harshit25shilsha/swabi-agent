from fastapi import APIRouter

from app.tools.package_tools import get_package_by_id,search_packages


router = APIRouter(
    prefix="/packages",
    tags=["Packages"]
)


@router.get("/{package_id}")
async def package_detail(package_id: int):
    return await get_package_by_id(package_id)


@router.get("/")
async def package_search(category: str):
    return await search_packages(category)