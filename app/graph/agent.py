import time

from app.services.groq_service import llm

from app.graph.tools import tools
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from app.graph.state import AgentState

from langchain_core.messages import SystemMessage, ToolMessage
from app.graph.prompts import build_system_prompt


from langgraph.graph import StateGraph, START

from langgraph.checkpoint.memory import MemorySaver
from app.core.logging import get_logger

logger = get_logger(__name__)

# Bind Tools To Groq

llm_with_tools = llm.bind_tools(tools)


def _trim_prior_tool_messages(messages: list) -> list:
    """
    Replace ToolMessages from prior turns with a short placeholder.
    Keeps the most recent turn's tool results intact for the LLM to
    use while composing its reply; trims everything older to avoid
    linear token growth across turns.
    """

    last_human_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if type(messages[i]).__name__ == "HumanMessage":
            last_human_idx = i
            break

    if last_human_idx is None:
        return messages

    trimmed = []
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage) and i < last_human_idx:
            trimmed.append(
                ToolMessage(
                    content="[tool result omitted from prior turn]",
                    tool_call_id=msg.tool_call_id
                )
            )
        else:
            trimmed.append(msg)

    return trimmed


# Create Agent Node

async def chatbot(state: AgentState):

    user_id = state.get("user_id")
    auth_user = state.get("auth_user")
    is_authenticated = state.get("is_authenticated", False)
    message_count = len(state.get("messages", []))

    logger.debug(
        "Chatbot node | user_id=%s | authenticated=%s | history=%d",
        user_id,
        is_authenticated,
        message_count,
    )
    
    # build system prompt with full auth context
    
    system_prompt = build_system_prompt(
        user_id=user_id,
        is_authenticated = is_authenticated,
        first_name = auth_user.first_name if auth_user else "",
        last_name = auth_user.last_name if auth_user else "",
        
    )

    messages = [
        SystemMessage(content= system_prompt),
        *_trim_prior_tool_messages(state["messages"])
    ]

    start = time.perf_counter()

    response = await llm_with_tools.ainvoke(messages)

    elapsed_ms = (time.perf_counter() - start) * 1000

    if response.tool_calls:
        logger.info(
            "LLM response | %.0fms | tools=%s",
            elapsed_ms,
            [tc["name"] for tc in  response.tool_calls],
        )
    else:
        logger.info(
            "LLM response | %.0fms | final | preview=%r",
            elapsed_ms,
            (response.content or "")[:120],
        )

    return {
        "messages": [response]
    }


# Create Tool Node

tool_node = ToolNode(
    tools=tools
)


def build_graph(checkpointer):

    builder = StateGraph(AgentState)
    builder.add_node("chatbot",chatbot)
    builder.add_node("tools",tool_node)
    builder.add_edge(START,"chatbot")

    # Conditional edge
    builder.add_conditional_edges("chatbot",tools_condition)

    # Tool returns to chatbot

    builder.add_edge("tools","chatbot")

    return builder.compile(
        checkpointer=checkpointer
    )

graph = build_graph(MemorySaver())