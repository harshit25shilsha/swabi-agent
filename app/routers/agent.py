import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage

from groq import APIStatusError

from app.core.auth import maybe_decode_token, AuthUser
from app.core.logging import get_logger
from app.schemas.chat import AgentRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


#  resolve identity for this turn 

async def _resolve_identity(
    body: AgentRequest,
    graph,
    config: dict,
) -> tuple[AuthUser | None, int | None]:
    """
    Determine who this request is from. Priority:

    1. Token in this request → decode → use that AuthUser (most trusted).
    2. auth_user already in session checkpoint → reuse from prior turn.
    3. user_id in this request (plain int, guest/dev) → use as-is.
    4. user_id already in session checkpoint → carry forward.
    5. None → guest session.

    Returns (auth_user, resolved_user_id).
    auth_user is None for unauthenticated/guest sessions.
    """
    
    if body.token:
        auth_user = maybe_decode_token(body.token)  # raises HTTPException if invalid
        return auth_user, auth_user.user_id if auth_user else None

    try:
        existing = await graph.aget_state(config)
        if existing and existing.values:
            stored_auth = existing.values.get("auth_user")
            if stored_auth:
                return stored_auth, stored_auth.user_id

            stored_uid = existing.values.get("user_id")
            if stored_uid:
                return None, stored_uid
    except Exception:
        pass

    if body.user_id:
        return None, body.user_id

    return None, None


# Main chat endpoint 

@router.post(
    "/",
    summary="Ask the AI travel agent",
    description=(
        "Send a travel query to the Swabi AI Agent. Pass a JWT in the "
        "`token` field (from POST /auth/login) to enable booking and "
        "personalized recommendations. Guest users can still search and "
        "get recommendations without a token."
    ),
)
async def agent_chat(
    request: Request,
    body: AgentRequest,
):
    graph      = request.app.state.graph
    session_id = body.session_id or str(uuid.uuid4())
    config     = {"configurable": {"thread_id": session_id}}

    auth_user, resolved_user_id = await _resolve_identity(body, graph, config)

    logger.info(
        "Agent request | session=%s | user_id=%s | authenticated=%s | new_session=%s | message=%r",
        session_id,
        resolved_user_id,
        auth_user is not None,
        body.session_id is None,
        (body.message or "")[:80],
    )

    try:
        result = await graph.ainvoke(
            {
                "messages":        [HumanMessage(content=body.message)],
                "user_id":         resolved_user_id,
                "auth_user":       auth_user,
                "is_authenticated": auth_user is not None,
            },
            config=config,
        )

    except APIStatusError as e:
        logger.error(
            "Groq API error | session=%s | user_id=%s | status=%s | detail=%s",
            session_id,
            resolved_user_id,
            e.status_code,
            str(e)[:200],
        )
        return JSONResponse(
            status_code=502,
            content={
                "response": (
                    "I ran into an issue generating a response for that "
                    "request. Could you try rephrasing it, or asking again?"
                ),
                "error":      "llm_tool_call_failed",
                "detail":     str(e),
                "session_id": session_id,
            },
        )

    logger.info(
        "Agent response | session=%s | user_id=%s | authenticated=%s | length=%d",
        session_id,
        resolved_user_id,
        auth_user is not None,
        len(result["messages"][-1].content or ""),
    )

    return {
        "response":        result["messages"][-1].content,
        "session_id":      session_id,
        "user_id":         resolved_user_id,
        "authenticated":   auth_user is not None,
    }


# Debug / history endpoints (unchanged from Phase 3) 

@router.get(
    "/debug/session/{session_id}",
    summary="[DEBUG] Inspect session state",
    description=(
        "Inspect what is checkpointed for a session_id without calling "
        "Groq. Now also shows auth_user identity. Remove before production."
    ),
)
async def debug_session_state(request: Request, session_id: str):
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    state  = await graph.aget_state(config)

    if not state or not state.values:
        return {"session_id": session_id, "found": False}

    messages  = state.values.get("messages", [])
    auth_user = state.values.get("auth_user")

    return {
        "session_id":      session_id,
        "found":           True,
        "authenticated":   auth_user is not None,
        "stored_user_id":  state.values.get("user_id"),
        "auth_user": {
            "user_id":    auth_user.user_id    if auth_user else None,
            "email":      auth_user.email      if auth_user else None,
            "user_type":  auth_user.user_type  if auth_user else None,
            "first_name": auth_user.first_name if auth_user else None,
        } if auth_user else None,
        "message_count":   len(messages),
        "messages": [
            {"role": type(m).__name__, "content": getattr(m, "content", "")}
            for m in messages
        ],
    }


@router.get(
    "/history/{session_id}",
    summary="Get conversation history for a session",
)
async def get_chat_history(request: Request, session_id: str):
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    state  = await graph.aget_state(config)

    if not state or not state.values:
        return {"session_id": session_id, "found": False, "message_count": 0, "messages": []}

    raw_messages = state.values.get("messages", [])
    ROLE_MAP     = {"HumanMessage": "user", "AIMessage": "assistant"}
    clean        = []
    turn         = 0

    for msg in raw_messages:
        role = ROLE_MAP.get(type(msg).__name__)
        if role is None:
            continue
        if role == "user":
            turn += 1
        content = getattr(msg, "content", "") or ""
        if role == "assistant" and not content.strip():
            continue
        clean.append({"turn": turn, "role": role, "content": content})

    return {
        "session_id":    session_id,
        "found":         True,
        "message_count": len(clean),
        "messages":      clean,
    }