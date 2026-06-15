import httpx

from app.config import settings


class SwabiClient:

    def __init__(self):
        self.base_url = settings.SWABI_API_BASE

    async def get(self, endpoint: str):

        async with httpx.AsyncClient() as client:

            response = await client.get(
                f"{self.base_url}{endpoint}"
            )

            response.raise_for_status()

            return response.json()


swabi_client = SwabiClient()