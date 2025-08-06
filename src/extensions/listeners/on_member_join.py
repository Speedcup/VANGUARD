import logging

from interactions import Client, Extension, listen
from interactions.api.events import MemberAdd

from src.common import Emoji, env


class OnMemberJoin(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot

    @listen(MemberAdd)
    async def on_member_join(self, event: MemberAdd) -> None:
        member = event.member

        channel = self.bot.get_channel(env.bot.member_log_channel)

        if not channel:
            logging.info(f'Channel with id={env.bot.member_log_channel} not found')
            return

        await channel.send(f'{Emoji.JOIN} {member.mention} ({member.display_name}) has joined!')
