import logging
from typing import List

from interactions import Activity, ActivityType, Client, Intents, Status


class Bot(Client):
    def __init__(self, token: str, owner_ids: List[str], logger: logging.Logger) -> None:
        super().__init__(
            activity=Activity(
                type=ActivityType.COMPETING,
                name='Valorant❤️',
            ),
            status=Status.DO_NOT_DISTURB,
            intents=Intents.ALL,
            disable_dm_commands=True,
            token=token,
            owner_ids=owner_ids,
            logger=logger,
        )

    async def bot_launch(self) -> None:
        await self.astart()
