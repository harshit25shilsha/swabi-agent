import httpx
from app.config import settings


class SwabiClient:

    def __init__(self):
        self.base_url = settings.SWABI_API_BASE

    #  Unauthenticated 

    async def get(self, endpoint: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def put(self, endpoint: str, payload: dict = None) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}{endpoint}",
                json=payload or {},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    # Authenticated (JWT Bearer) 

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def get_authed(self, endpoint: str, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self._auth_headers(token),
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def post_authed(self, endpoint: str, payload: dict, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=self._auth_headers(token),
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def put_authed(self, endpoint: str, payload: dict, token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=self._auth_headers(token),
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()


swabi_client = SwabiClient()