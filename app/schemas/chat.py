from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="Message to send to the Swabi AI assistant.",
        examples=[
            "Show me adventure activities in Uttarakhand",
            "Find pilgrimage packages",
            "Plan a trip to Rishikesh"
        ]
    )


class AgentRequest(BaseModel):
    message:str = Field(
        ...,
        description="Travel question or request for the LangGraph AI Agent.",
        examples=[
            "Show adventure activities in Uttarakhand",
            "Find pilgrimage packages"
            "Find package details for package 4",
        ],
    )
    
    # Auth Token
    token: Optional[str] = Field(
        None,
        description=(
            "JWT from POST /auth/login. Send on the first turn of a "
            "new authenticated session. The agent stores it in session "
            "state and uses it for protected API calls (booking, etc.). "
            "Guest users omit this field — they can search and recommend "
            "but cannot book."
        ),
        examples=["abcxyz....."]
    )
    
    user_id : Optional[int] = Field(
        None,
        description=(
            "Swabi user_id for guest/dev use. Ignored when token is "
            "provided — user_id is always extracted from the JWT in "
            "authenticated sessions."
        ),
        examples=[2,3],
    )
    
    session_id: Optional[str] = Field(
        None,
        description=(
            "Identifies this conversation across turns. Omit on the "
            "first message — the server generates one and returns it. "
            "Pass it back on every subsequent turn in the same chat."
        ),
        examples=["b3ref-dfrfsd..........."],
    )