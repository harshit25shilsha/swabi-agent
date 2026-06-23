import time
from app.services.groq_service import llm

from app.graph.tools import tools
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from app.graph.state import AgentState

from langchain_core.messages import SystemMessage
from app.graph.prompts import build_system_prompt

from langgraph.graph import (
    StateGraph,
    START
)

from langgraph.checkpoint.memory import MemorySaver
from app.core.logging import get_logger
logger = get_logger(__name__)

# Bind Tools To Groq

llm_with_tools = llm.bind_tools(tools)


# Create Agent Node

async def chatbot(state):
    user_id = state.get("user_id")
    message_count = len(state.get("message",[]))
    logger.debug(
        "Chatbot node invoked | user_id = %s | history_length = %d",
        user_id,
        message_count
    )
    
    messages = [
        SystemMessage(content=build_system_prompt(state.get("user_id"))),
        *state["messages"]
    ]
    
    start_time = time.perf_counter()

    response = await llm_with_tools.ainvoke(
        messages
    )
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    if response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        
        logger.info(
            "LLM response | elapsed=%.0fms | tool_calls=%s",
            elapsed_ms,
            tool_names
        )
    else:
        response_preview = (response.content or "")[:120]
        logger.info(
            "LLM response | elapsed=%.0fms | final answer | preview=%r",
            elapsed_ms,
            response_preview
        )
        
    return {
        "messages": [response]
    }


# Create Tool Node

tool_node = ToolNode(
    tools=tools
)


def build_graph(checkpointer):
    """
    Build and compile the agent graph with the given checkpointer.

    Kept as a factory function (rather than only a module-level
    compiled graph) so the app can choose its checkpointer at startup —
    an in-memory MemorySaver for quick local testing, or a persistent
    AsyncSqliteSaver (see app/main.py) for conversation history that
    survives a server restart. Different checkpointers are NOT
    interchangeable after compile time, so the choice has to be made
    before compiling, not patched in afterward.
    """

    builder = StateGraph(
        AgentState
    )

    builder.add_node(
        "chatbot",
        chatbot
    )

    builder.add_node(
        "tools",
        tool_node
    )

    builder.add_edge(
        START,
        "chatbot"
    )

    # Conditional edge

    builder.add_conditional_edges(
        "chatbot",
        tools_condition
    )

    # Tool returns to chatbot

    builder.add_edge(
        "tools",
        "chatbot"
    )

    return builder.compile(
        checkpointer=checkpointer
    )



graph = build_graph(MemorySaver())