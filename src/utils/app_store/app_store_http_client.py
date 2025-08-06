from httpx import AsyncClient

from .types import AppStoreResponse


class AppStoreHttpClient:
    def __init__(self, client: AsyncClient):
        self.client = client

    async def get_release(self) -> AppStoreResponse:
        response = await self.client.get(
            url='https://itunes.apple.com/lookup?id=6476132885',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
            },
            timeout=60.0,
        )

        data = response.json()

        return AppStoreResponse(**data)
