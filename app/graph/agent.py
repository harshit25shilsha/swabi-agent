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

# Bind Tools To Groq

llm_with_tools = llm.bind_tools(tools)


# Create Agent Node

async def chatbot(state):

    messages = [
        SystemMessage(content=build_system_prompt(state.get("user_id"))),
        *state["messages"]
    ]

    print("\nSTATE:")
    print(messages)

    response = await llm_with_tools.ainvoke(
        messages
    )

    print("\nRESPONSE:")
    print(response)

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