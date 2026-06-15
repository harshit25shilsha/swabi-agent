from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.services.groq_service import llm


router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):

    response = llm.invoke(
        request.message
    )

    return {
        "response": response.content
    }