from httpx import AsyncClient
from interactions import Client, Extension, IntervalTrigger, Task

from src.common import env
from src.components import AppStoreContainer
from src.database import AppStoreAppController
from src.utils import AppStoreHttpClient


class AppStoreCheckAppVersion(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.app_store_http_client = AppStoreHttpClient(AsyncClient())
        self.app_store_container = AppStoreContainer
        self.app_store_app_controller = AppStoreAppController()

    async def async_start(self):
        self.app_store_check.start()

    @Task.create(IntervalTrigger(minutes=10))
    async def app_store_check(self) -> None:
        get_release = await self.app_store_http_client.get_release()
        result = get_release.results[0]
        app_version = await self.app_store_app_controller.get_by_version(result.version)

        if not app_version:
            await self.app_store_app_controller.create(
                result.version, result.release_notes, result.release_date
            )
            channel = await self.client.fetch_channel(channel_id=env.bot.app_store_updates_channel)

            if channel:
                component = self.app_store_container(
                    result.version, result.release_notes, result.release_date
                ).build()

                await channel.send(components=component)
