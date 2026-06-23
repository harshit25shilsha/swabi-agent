import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage

from groq import APIStatusError

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)



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


@router.get(
    "/history/{session_id}",
    summary="Get conversation history for a session",
    description=(
        "Returns the full conversation history for a session_id in a clean, "
        "frontend-consumable format — alternating user and assistant messages "
        "grouped by turn number. Use this to display a past conversation, "
        "resume a session after a page reload, or validate multi-turn "
        "workflows end-to-end. Returns an empty message list (not a 404) "
        "if the session exists but has no messages yet."
    )
)
async def get_chat_history(
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
            "message_count": 0,
            "messages": []
        }

    raw_messages = state.values.get("messages", [])

    ROLE_MAP = {
        "HumanMessage": "user",
        "AIMessage": "assistant",
    }

    clean_messages = []
    turn = 0

    for msg in raw_messages:
        role = ROLE_MAP.get(type(msg).__name__)
        if role is None:
            continue

        if role == "user":
            turn += 1

        content = getattr(msg, "content", "") or ""

       
        if role == "assistant" and not content.strip():
            continue

        clean_messages.append({
            "turn": turn,
            "role": role,
            "content": content
        })

    logger.debug(
        "Chat history retrieved | session=%s | messages=%d",
        session_id,
        len(clean_messages)
    )

    return {
        "session_id": session_id,
        "found": True,
        "message_count": len(clean_messages),
        "messages": clean_messages
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
            pass

    logger.info(
        "Agent request | session=%s | user_id=%s | new_session=%s | message=%r",
        session_id,
        resolved_user_id,
        body.session_id is None,
        (body.message or "")[:80]
    )

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
        logger.error(
            "Groq API error | session=%s | user_id=%s | status=%s | detail=%s",
            session_id,
            resolved_user_id,
            e.status_code,
            str(e)[:200]
        )
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

    logger.info(
        "Agent response | session=%s | user_id=%s | response_length=%d",
        session_id,
        resolved_user_id,
        len(result["messages"][-1].content or "")
    )

    return {
        "response": result["messages"][-1].content,
        "session_id": session_id
    }