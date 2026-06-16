from fastapi import APIRouter

from langchain_core.messages import HumanMessage

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


@router.post(
    "/",
    summary="Ask the AI travel agent",
    description=(
        "Send a travel query to the Swabi AI Agent. The agent can search "
        "activities, search packages, fetch package details, and recommend trips. "
        "Try: 'Show adventure activities in Uttarakhand' or "
        "'Show package details for package 4'."
    )
)
async def agent_chat(
    request: AgentRequest
):

    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=request.message
                )
            ]
        }
    )

    return {
        "response":
            result["messages"][-1].content
    }
