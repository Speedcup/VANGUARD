from interactions import Embed as iEmbed, EmbedAttachment
from models.colors import Colors
from models.const import VALPAW_LOGO


class Embed(iEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.color:
            self.color = Colors.PRIMARY

        if not self.thumbnail:
            self.thumbnail = EmbedAttachment(url=VALPAW_LOGO)
