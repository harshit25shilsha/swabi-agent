from app.services.groq_service import llm

from app.graph.tools import tools
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from app.graph.state import AgentState

from langchain_core.messages import SystemMessage
from app.graph.prompts import SYSTEM_PROMPT

from langgraph.graph import (
    StateGraph,
    START
)

# Bind Tools To Groq

llm_with_tools = llm.bind_tools(tools)


# Create Agent Node

async def chatbot(state):

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
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

# Build Graph

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

graph = builder.compile()