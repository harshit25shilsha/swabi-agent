from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="Message to send to the Swabi AI assistant.",
        examples=[
            "Show me adventure activities in Uttarakhand",
            "Find pilgrimage packages",
            "Plan a trip to Rishikesh"
        ]
    )
