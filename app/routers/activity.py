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
        "Search active Swabi activities by optional country, state, city, "
        "category, and maximum price. "
        "Example: country=India, state=Uttarakhand, category=Adventure, max_price=2000."
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
    city: str = Query(
        None,
        description="City filter for activity results (substring match).",
        examples=["Agra"]
    ),
    category: str = Query(
        None,
        description="Activity category filter such as Adventure, Hiking, or Camping.",
        examples=["Adventure"]
    ),
    max_price: float = Query(
        None,
        description="Maximum activity price per person.",
        examples=[2000]
    )
):

    return await search_activities(
        country=country,
        state=state,
        city=city,
        category=category,
        max_price=max_price
    )
