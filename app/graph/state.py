from typing import Annotated, Optional
from dataclasses import dataclass

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.core.auth import AuthUser


class AgentState(TypedDict):
    #  existing fields 
    messages: Annotated[list, add_messages]
    user_id:  Optional[int]

    #  auth fields 
    # Full authenticated identity — set once on the first authenticated
    # turn and persisted in the checkpoint for the rest of the session.
    # Tools that need to call protected Swabi APIs (booking, etc.) read
    # auth_user.token from state rather than receiving it as a parameter.
    auth_user: Optional[AuthUser]

    # Convenience flag so the chatbot node and prompts can cheaply check
    # whether this session is authenticated without inspecting auth_user.
    is_authenticated: bool