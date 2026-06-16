from langgraph.graph import StateGraph
from langgraph.graph import END

from app.graph.state import TravelAgentState

from app.agents.supervisor import supervisor
from app.agents.conversation import conversation_agent


builder = StateGraph(TravelAgentState)

builder.add_node(
    "supervisor",
    supervisor
)

builder.add_node(
    "conversation",
    conversation_agent
)


builder.set_entry_point("supervisor")


def route(state: TravelAgentState):

    if state["current_agent"] == "conversation":
        return "conversation"

    return END


builder.add_conditional_edges(
    "supervisor",
    route,
    {
        "conversation": "conversation",
        END: END,
    },
)

builder.add_edge(
    "conversation",
    END,
)

travel_graph = builder.compile()