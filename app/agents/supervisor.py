from app.graph.state import TravelAgentState


def supervisor(state: TravelAgentState):

    preferences = state.get("preferences", {})

    required = [
        "destination",
        "budget",
        "travellers",
        "start_date"
    ]

    for item in required:

        if not preferences.get(item):

            state["current_agent"] = "conversation"

            return state

    state["current_agent"] = "search"

    return state