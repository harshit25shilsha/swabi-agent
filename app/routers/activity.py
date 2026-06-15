from fastapi import APIRouter

from app.tools.activity_tools import search_activities

router = APIRouter(
    prefix="/activities",
    tags=["Activities"]
)


@router.get("/")
async def activities(
    country: str = None,
    state: str = None,
    category: str = None
):

    return await search_activities(
        country = country,
        state=state,
        category=category
    )
