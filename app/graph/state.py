from typing import TypedDict, List, Dict, Optional


class TravelAgentState(TypedDict):

    # Complete conversation
    messages: List[Dict]

    # Extracted user preferences
    preferences: Dict

    # Current search results
    packages: List[Dict]

    # Current booking
    booking: Optional[Dict]

    # Current active agent
    current_agent: str

    # Missing fields
    missing_fields: List[str]

    # Final response
    response: str