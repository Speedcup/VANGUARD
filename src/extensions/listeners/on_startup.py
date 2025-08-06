import logging

from interactions import Client, Extension, listen
from interactions.api.events import Startup
from tortoise import Tortoise

from src.common import env


class OnStartup(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot

    @listen(Startup)
    async def on_startup(self) -> None:
        await Tortoise.init(env.database.tortoise_orm)
        logging.info(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
