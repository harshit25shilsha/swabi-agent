import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage

from groq import APIStatusError

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
            "if it's needed and missing. Once set for a session, it carries "
            "forward to later turns in that same session even if omitted."
        ),
        examples=[2, 3]
    )

    session_id: str = Field(
        None,
        description=(
            "Identifies this conversation so the agent remembers earlier "
            "turns within it. Pass the same session_id on every request in "
            "the same conversation; omit it on the first message of a new "
            "conversation and the server will generate one, returned in "
            "the response — store it and send it back on subsequent turns. "
            "Different sessions never share message history, even for the "
            "same user_id."
        ),
        examples=["b3f1c2a4-7e21-4c3a-9d3f-2a6b7c8d9e10"]
    )


@router.get(
    "/debug/session/{session_id}",
    summary="[DEBUG] Inspect a session's stored conversation state",
    description=(
        "Developer-only endpoint to inspect what's currently checkpointed "
        "for a session_id (message history, stored user_id) WITHOUT calling "
        "Groq. Useful for confirming memory/session behavior when you're "
        "rate-limited or just want to verify state server-side. "
        "Consider removing this endpoint before any real deployment — it "
        "exposes raw conversation content with no auth check."
    )
)
async def debug_session_state(
    request: Request,
    session_id: str
):

    graph = request.app.state.graph

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    state = await graph.aget_state(config)

    if not state or not state.values:
        return {
            "session_id": session_id,
            "found": False,
            "message": "No checkpoint exists yet for this session_id."
        }

    messages = state.values.get("messages", [])

    return {
        "session_id": session_id,
        "found": True,
        "stored_user_id": state.values.get("user_id"),
        "message_count": len(messages),
        "messages": [
            {
                "role": type(m).__name__,
                "content": getattr(m, "content", "")
            }
            for m in messages
        ]
    }


@router.post(
    "/",
    summary="Ask the AI travel agent",
    description=(
        "Send a travel query to the Swabi AI Agent. The agent can search "
        "activities, search packages, fetch package details, and recommend trips. "
        "Pass user_id to enable personalized recommendations, and session_id to "
        "maintain conversation memory across multiple turns. "
        "Try: 'Show adventure activities in Uttarakhand' or "
        "'Show package details for package 4'."
    )
)
async def agent_chat(
    request: Request,
    body: AgentRequest
):

    graph = request.app.state.graph

    
    session_id = body.session_id or str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

   
    resolved_user_id = body.user_id

    if resolved_user_id is None:
        try:
            existing_state = await graph.aget_state(config)
            if existing_state and existing_state.values:
                resolved_user_id = existing_state.values.get("user_id")
        except Exception:
            # No prior checkpoint for this thread_id yet (new session) —
            # nothing to fall back to, proceed with user_id=None.
            pass

    try:
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content=body.message
                    )
                ],
                "user_id": resolved_user_id
            },
            config=config
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
                "detail": str(e),
                "session_id": session_id
            }
        )

    return {
        "response": result["messages"][-1].content,
        "session_id": session_id
    }