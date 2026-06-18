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

# CheckPointer enables conversation memory: Langgraph will persist 

# MemorySaver is IN-Memory Only : History live in this Python
# process's memory and is lost on restart (including uvicorn --reload)

checkpointer = MemorySaver()

graph = builder.compile(
    checkpointer = checkpointer
)