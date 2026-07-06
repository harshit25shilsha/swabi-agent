
import httpx
 
from app.services.swabi_client import swabi_client
 
COUNTRIESNOW_BASE = "https://countriesnow.space/api/v0.1"
 
 
async def get_countries() -> list:
    """All countries with iso codes. Client-side shape:
    [{"country": "Afghanistan", "iso2": "AF", "iso3": "AFG"}, ...]"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{COUNTRIESNOW_BASE}/countries", timeout=30.0)
        response.raise_for_status()
        data = response.json()
 
    return [
        {"country": c.get("country"), "iso2": c.get("iso2"), "iso3": c.get("iso3")}
        for c in data.get("data", [])
        if c.get("country")
    ]
 
 
async def get_states_for_country(country: str) -> list:
    """States/provinces for one country. Returns [] if the country isn't
    found or genuinely has no states on file."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{COUNTRIESNOW_BASE}/countries/states",
            params={"country": country},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
 
    target = country.strip().lower()
    for entry in data.get("data", []):
        if (entry.get("name") or "").strip().lower() == target:
            return [s.get("name") for s in entry.get("states", []) if s.get("name")]
    return []
 
 
async def get_user_by_id(user_id: int, token: str) -> dict:
    """Basic Swabi account info — name, mobile, address, country, state —
    used to prefill the primary traveler on the Add Members screen."""
    response = await swabi_client.get_authed(
        f"/user/get_user_by_userId?userId={user_id}", token,
    )
    return response.get("data") or response