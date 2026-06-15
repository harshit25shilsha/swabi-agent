from fastapi import APIRouter

from app.tools.activity_tools import search_activities

router = APIRouter(
    prefix="/activities",
    tags=["Activities"]
)


@router.get("/")
async def activities(
    state: str = None,
    category: str = None
):

    return await search_activities(
        state=state,
        category=category
    )
