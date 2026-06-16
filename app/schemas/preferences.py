from typing import Optional, List

from pydantic import BaseModel


class TravelPreferences(BaseModel):

    destination: Optional[str] = None

    budget: Optional[int] = None

    travellers: Optional[int] = None

    start_date: Optional[str] = None

    duration_days: Optional[int] = None

    departure_city: Optional[str] = None

    hotel_type: Optional[str] = None

    transport: Optional[str] = None

    activities: List[str] = []

    category: Optional[str] = None