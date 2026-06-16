from fastapi import APIRouter, Query

from app.tools.activity_tools import search_activities

router = APIRouter(
    prefix="/activities",
    tags=["Activities"]
)


@router.get(
    "/",
    summary="Search activities",
    description=(
        "Search active Swabi activities by optional country, state, and category. "
        "Example: country=India, state=Uttarakhand, category=Adventure."
    )
)
async def activities(
    country: str = Query(
        None,
        description="Country filter for activity results.",
        examples=["India"]
    ),
    state: str = Query(
        None,
        description="State or region filter for activity results.",
        examples=["Uttarakhand"]
    ),
    category: str = Query(
        None,
        description="Activity category filter such as Adventure, Hiking, or Camping.",
        examples=["Adventure"]
    )
):

    return await search_activities(
        country = country,
        state=state,
        category=category
    )
