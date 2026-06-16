from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.services.groq_service import llm


router = APIRouter(
    tags=["Chat"]
)


@router.post(
    "/chat",
    summary="Chat with the AI assistant",
    description=(
        "Send a simple message directly to the Groq chat model. "
        "Use /agent for tool-based activity, package, and trip recommendation requests."
    )
)
async def chat(request: ChatRequest):

    response = llm.invoke(
        request.message
    )

    return {
        "response": response.content
    }
