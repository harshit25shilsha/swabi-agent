from app.services.swabi_client import swabi_client


async def get_package_by_id(
    package_id: int
):
    return await swabi_client.get(
        f"/package/get_package_by_id?packageId={package_id}"
    )


async def search_packages(
    category: str = None
):

    if not category:
        return {
            "message": "category is required"
        }

    return await swabi_client.get(
        f"/package/get_package_list_by_category?categoryName={category}&pageNumber=-1&pageSize=-1"
    )


async def recommend_packages(
    category=None,
    state=None,
    country=None,
    max_budget=None,
    duration=None
):
    """
    Placeholder implementation.
    Can be enhanced later with
    budget, duration and location filters.
    """

    return await search_packages(category)