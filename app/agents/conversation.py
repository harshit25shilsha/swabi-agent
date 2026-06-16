from app.services.groq_service import llm

from app.schemas.preferences import TravelPreferences

from app.graph.state import TravelAgentState


REQUIRED_FIELDS = [

    "destination",

    "budget",

    "travellers",

    "start_date"
]


structured_llm = llm.with_structured_output(
    TravelPreferences
)


SYSTEM_PROMPT = """
Extract travel preferences from the user.

Return only structured data.

If a value is missing keep it null.

Do not guess.

If activities are mentioned return them as list.
"""


def conversation_agent(state: TravelAgentState):

    messages = state["messages"]

    user_text = messages[-1]["content"]

    extracted = structured_llm.invoke(

        SYSTEM_PROMPT + "\n\nUser:\n" + user_text

    )

    preferences = state.get("preferences", {})

    extracted = extracted.model_dump()

    for key, value in extracted.items():

        if value not in [None, "", []]:

            preferences[key] = value

    state["preferences"] = preferences

    missing = []

    for field in REQUIRED_FIELDS:

        if not preferences.get(field):

            missing.append(field)

    state["missing_fields"] = missing

    if missing:

        pretty = "\n".join(

            f"- {item.replace('_',' ').title()}"

            for item in missing

        )

        state["response"] = (

            "Great! I've understood your travel request.\n\n"

            "I still need:\n\n"

            f"{pretty}"

        )

    else:

        state["response"] = (

            "Perfect! I have enough information."

            " I'll now search for matching travel packages."

        )

    return state