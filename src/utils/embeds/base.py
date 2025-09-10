from datetime import datetime

from interactions import Embed as InteractionsEmbed, Timestamp
from pytz import utc

from src.common import VALPAW_LOGO, Colors


class Embed(InteractionsEmbed):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            color=Colors.PRIMARY,
            thumbnail=VALPAW_LOGO,
            timestamp=Timestamp.fromdatetime(datetime.now(utc)),
            **kwargs,
        )
