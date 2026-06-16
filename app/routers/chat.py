from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.services.groq_service import llm

from app.graph.builder import travel_graph


router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):

    state = {

        "messages": [
            {
                "role": "user",
                "content": request.message
            }
        ],

        "preferences": {},

        "packages": [],

        "booking": None,

        "current_agent": "",

        "missing_fields": [],

        "response": ""
    }

    result = travel_graph.invoke(state)

    return {
        "response": result["response"],
        "state": result
    }
