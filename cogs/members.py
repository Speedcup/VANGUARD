"""Member join/leave/ban logging.

Wording and emoji visuals are preserved verbatim from the legacy bot; only the
implementation is refactored to discord.py idioms.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.client import VanguardBot

log = logging.getLogger("vanguard.cog.members")


class Members(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot

    def _log_channel(self) -> discord.abc.Messageable | None:
        channel_id = self.bot.config.member_log_channel_id
        if channel_id is None:
            return None
        channel = self.bot.get_channel(channel_id)
        return channel if isinstance(channel, discord.abc.Messageable) else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        channel = self._log_channel()
        if channel is None:
            return
        await channel.send(
            f"<:icons_join:1275889849009836082> {member.mention} "
            f"({member.display_name}) has joined!"
        )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel = self._log_channel()
        if channel is None:
            return

        # A valid ban entry on leave means they left because of the ban.
        try:
            ban = await member.guild.fetch_ban(member)
        except discord.NotFound:
            ban = None
        except discord.HTTPException as exc:
            log.warning("Failed to fetch ban for %s: %s", member, exc)
            ban = None

        if ban is not None:
            ban_reason = f"```{ban.reason}```" if ban.reason else ""
            await channel.send(
                f"<:icons_ban:1275889713890201620> {member.mention} "
                f"({member.display_name}) got banned!{ban_reason}"
            )
            return

        await channel.send(
            f"<:icons_leave:1275889855649550356> {member.mention} "
            f"({member.display_name}) has left!"
        )


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(Members(bot))
