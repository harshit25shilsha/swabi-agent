from fastapi import APIRouter
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage

from groq import APIStatusError

from app.graph.agent import graph
from pydantic import BaseModel, Field



router = APIRouter(
    prefix="/agent",
    tags=["Agent"]
)


class AgentRequest(BaseModel):

    message: str = Field(
        ...,
        description="Travel question or request for the LangGraph AI agent.",
        examples=[
            "Show adventure activities in Uttarakhand",
            "Find pilgrimage packages",
            "Show package details for package 4"
        ]
    )

    user_id: int = Field(
        None,
        description=(
            "Swabi user id for the logged-in user, if known. When provided, "
            "the agent can give personalized recommendations based on the "
            "user's booking history, search history, and stated preferences. "
            "Omit this for guest users or when the frontend hasn't resolved "
            "a logged-in user yet — the agent will ask for it conversationally "
            "if it's needed and missing."
        ),
        examples=[2, 3]
    )


@router.post(
    "/",
    summary="Ask the AI travel agent",
    description=(
        "Send a travel query to the Swabi AI Agent. The agent can search "
        "activities, search packages, fetch package details, and recommend trips. "
        "Pass user_id to enable personalized recommendations. "
        "Try: 'Show adventure activities in Uttarakhand' or "
        "'Show package details for package 4'."
    )
)
async def agent_chat(
    request: AgentRequest
):

    try:
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content=request.message
                    )
                ],
                "user_id": request.user_id
            }
        )

    except APIStatusError as e:

        return JSONResponse(
            status_code=502,
            content={
                "response": (
                    "I ran into an issue generating a response for that "
                    "request. Could you try rephrasing it, or asking again?"
                ),
                "error": "llm_tool_call_failed",
                "detail": str(e)
            }
        )

    return {
        "response":
            result["messages"][-1].content
    }