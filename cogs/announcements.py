"""Auto-publish messages posted in announcement (news) channels."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.client import VanguardBot

log = logging.getLogger("vanguard.cog.announcements")


class Announcements(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if message.channel.type is not discord.ChannelType.news:
            return
        # Skip system messages (pins, joins, etc.); only crosspost real content.
        if message.type not in (discord.MessageType.default, discord.MessageType.reply):
            return

        try:
            await message.publish()
            await message.add_reaction("\U0001f4e3")  # :mega:
        except discord.HTTPException as exc:
            # Crossposting can fail or be rate-limited; log and move on.
            log.warning("Failed to publish announcement in #%s: %s", message.channel, exc)


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(Announcements(bot))
