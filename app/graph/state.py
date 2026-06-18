from typing import TypedDict, Annotated, Optional

from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: Optional[int]