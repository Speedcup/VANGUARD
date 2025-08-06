import logging

from interactions import Client, Extension, listen
from interactions.api.events import MemberRemove

from src.common import Emoji, env


class OnMemberRemove(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot

    @listen(MemberRemove)
    async def on_member_remove(self, event: MemberRemove) -> None:
        member = event.member

        channel = self.bot.get_channel(env.bot.member_log_channel)

        if not channel:
            logging.info(f'Channel with id={env.bot.member_log_channel} not found')
            return

        ban_entry = await member.guild.fetch_ban(member)

        if ban_entry:
            await channel.send(
                f'{Emoji.BAN} {member.mention} ({member.display_name}) was banned!\n\nReason: ```{ban_entry.reason if ban_entry.reason else ""}```'
            )
            return

        await channel.send(
            f'{Emoji.LEAVE} {member.mention} ({member.display_name}) has left the server.'
        )
