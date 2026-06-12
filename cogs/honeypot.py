"""Honeypot trap for compromised member accounts.

A legitimate member whose account is compromised often starts spamming every
channel. A honeypot channel that real members are told never to post in catches
exactly that: any post triggers a *softban* (ban to purge the account's recent
messages, then an automatic unban) so the spam stops, the mess is cleaned up, and
the real owner can rejoin clean once they regain access. It is intentionally not
a permanent ban.

Because this acts automatically, the trigger is guarded hard: bots, staff/exempt
roles, and anyone with ban/admin/manage-guild permissions are never caught.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import VanguardBot
from ui.embeds import DANGER, branded_embed
from ui.honeypot_view import HoneypotWarningView
from utils.checks import staff_only

log = logging.getLogger("vanguard.cog.honeypot")

# Purge the compromised account's last hour of messages server-wide in one call.
_PURGE_SECONDS = 3600


def _build_warning_embed() -> discord.Embed:
    return branded_embed(
        title="\u26d4 DO NOT POST IN THIS CHANNEL",
        description=(
            "This channel is an **automated security trap**.\n\n"
            "It exists to catch **compromised accounts** that start spamming. "
            "Posting anything here will get your account **automatically removed** "
            "from the server to stop the spam.\n\n"
            "If you can read this: simply **do not post here** and you'll be fine."
        ),
        color=DANGER,
    )


class Honeypot(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot
        self._trap_channels: set[int] = set()
        self._pending_unbans: set[asyncio.Task[None]] = set()

    async def cog_load(self) -> None:
        self._trap_channels = await self.bot.honeypot_repo.enabled_channel_ids()
        log.info("Loaded %d active honeypot channel(s).", len(self._trap_channels))

    # ------------------------------------------------------------------ #
    # Settings helpers                                                    #
    # ------------------------------------------------------------------ #
    async def _softban_seconds(self) -> int:
        return await self.bot.settings_repo.get_int(
            "honeypot_softban_seconds", self.bot.config.honeypot_softban_seconds
        )

    async def _exempt_roles(self) -> set[int]:
        return await self.bot.settings_repo.get_id_set("honeypot_exempt_roles")

    async def _dm_on_unban(self) -> bool:
        return (await self.bot.settings_repo.get("honeypot_dm_on_unban", "0")) == "1"

    # ------------------------------------------------------------------ #
    # Command group                                                       #
    # ------------------------------------------------------------------ #
    honeypot = app_commands.Group(
        name="honeypot",
        description="Manage compromised-account honeypot traps (staff only).",
    )

    @honeypot.command(name="setup", description="Designate a channel as a honeypot trap.")
    @app_commands.describe(channel="The channel to turn into a trap")
    @staff_only()
    async def setup_trap(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        assert interaction.guild is not None
        me = interaction.guild.me

        # Permission preflight: warn now rather than fail silently at trigger time.
        missing: list[str] = []
        if not me.guild_permissions.ban_members:
            missing.append("Ban Members")
        channel_perms = channel.permissions_for(me)
        if not channel_perms.send_messages:
            missing.append(f"Send Messages in {channel.mention}")
        if not me.guild_permissions.manage_messages:
            missing.append("Manage Messages")
        if missing:
            await interaction.response.send_message(
                "\u26a0\ufe0f I'm missing required permissions: "
                + ", ".join(missing)
                + ".\nGrant them, then run setup again.",
                ephemeral=True,
            )
            return

        existing = await self.bot.honeypot_repo.get(channel.id)
        caught = existing.caught_count if existing else 0

        warning = await channel.send(
            embed=_build_warning_embed(),
            view=HoneypotWarningView(caught),
        )
        await self.bot.honeypot_repo.upsert(
            channel_id=channel.id,
            guild_id=interaction.guild.id,
            embed_message_id=warning.id,
        )
        self._trap_channels.add(channel.id)

        await interaction.response.send_message(
            f"\u2705 {channel.mention} is now an active honeypot trap.", ephemeral=True
        )

    @honeypot.command(name="disable", description="Disable a honeypot trap channel.")
    @app_commands.describe(channel="The trap channel to disable")
    @staff_only()
    async def disable_trap(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ) -> None:
        disabled = await self.bot.honeypot_repo.disable(channel.id)
        self._trap_channels.discard(channel.id)
        if disabled:
            await interaction.response.send_message(
                f"\u2705 Disabled the honeypot in {channel.mention}.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"\u26a0\ufe0f {channel.mention} was not an active trap.", ephemeral=True
            )

    @honeypot.command(name="status", description="Show honeypot configuration and stats.")
    @staff_only()
    async def status(self, interaction: discord.Interaction) -> None:
        exempt = await self._exempt_roles()
        exempt_text = ", ".join(f"<@&{rid}>" for rid in exempt) if exempt else "None"
        traps = (
            ", ".join(f"<#{cid}>" for cid in self._trap_channels)
            if self._trap_channels
            else "None"
        )
        embed = branded_embed(title="Honeypot Status", color=DANGER)
        embed.add_field(name="Active traps", value=traps, inline=False)
        embed.add_field(name="Softban duration", value=f"{await self._softban_seconds()}s", inline=True)
        embed.add_field(name="DM on unban", value="On" if await self._dm_on_unban() else "Off", inline=True)
        embed.add_field(name="Exempt roles", value=exempt_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @honeypot.command(name="duration", description="Set how long a softban lasts before auto-unban.")
    @app_commands.describe(seconds="Seconds before the account is automatically unbanned")
    @staff_only()
    async def set_duration(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 10, 86400]
    ) -> None:
        await self.bot.settings_repo.set("honeypot_softban_seconds", str(seconds))
        await interaction.response.send_message(
            f"\u2705 Softban duration set to {seconds}s.", ephemeral=True
        )

    @honeypot.command(name="dm_on_unban", description="Toggle DMing the affected user on unban.")
    @app_commands.describe(enabled="Whether to DM the user a heads-up when they're unbanned")
    @staff_only()
    async def toggle_dm(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.settings_repo.set("honeypot_dm_on_unban", "1" if enabled else "0")
        await interaction.response.send_message(
            f"\u2705 DM-on-unban is now {'on' if enabled else 'off'}.", ephemeral=True
        )

    @honeypot.command(name="exempt_add", description="Exempt a role from the honeypot trap.")
    @app_commands.describe(role="Role whose members are never caught")
    @staff_only()
    async def exempt_add(self, interaction: discord.Interaction, role: discord.Role) -> None:
        exempt = await self._exempt_roles()
        exempt.add(role.id)
        await self.bot.settings_repo.set_id_set("honeypot_exempt_roles", exempt)
        await interaction.response.send_message(
            f"\u2705 {role.mention} is now exempt from the honeypot.", ephemeral=True
        )

    @honeypot.command(name="exempt_remove", description="Remove a role's honeypot exemption.")
    @app_commands.describe(role="Role to stop exempting")
    @staff_only()
    async def exempt_remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        exempt = await self._exempt_roles()
        exempt.discard(role.id)
        await self.bot.settings_repo.set_id_set("honeypot_exempt_roles", exempt)
        await interaction.response.send_message(
            f"\u2705 {role.mention} is no longer exempt.", ephemeral=True
        )

    # ------------------------------------------------------------------ #
    # Trigger                                                             #
    # ------------------------------------------------------------------ #
    async def _is_exempt(self, member: discord.Member, exempt_roles: set[int]) -> bool:
        if member.bot or member.guild.owner_id == member.id:
            return True
        perms = member.guild_permissions
        if perms.administrator or perms.ban_members or perms.manage_guild:
            return True
        member_role_ids = {role.id for role in member.roles}
        if self.bot.config.staff_role_id in member_role_ids:
            return True
        return bool(member_role_ids & exempt_roles)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.channel.id not in self._trap_channels:
            return
        if message.guild is None or not isinstance(message.author, discord.Member):
            return
        if message.author.bot:
            return

        member = message.author
        exempt_roles = await self._exempt_roles()
        if await self._is_exempt(member, exempt_roles):
            return

        await self._catch(message, member)

    async def _catch(self, message: discord.Message, member: discord.Member) -> None:
        guild = message.guild
        assert guild is not None

        trigger_content = message.content or "(no text content)"
        try:
            await guild.ban(
                member,
                reason="Honeypot: suspected compromised account (softban).",
                delete_message_seconds=_PURGE_SECONDS,
            )
        except discord.Forbidden:
            log.error("Honeypot trigger but missing permission to ban %s.", member)
            return
        except discord.HTTPException as exc:
            log.error("Honeypot failed to ban %s: %s", member, exc)
            return

        # Schedule the auto-unban so the account can rejoin once recovered.
        duration = await self._softban_seconds()
        task = asyncio.create_task(self._schedule_unban(guild, member.id, duration))
        self._pending_unbans.add(task)
        task.add_done_callback(self._pending_unbans.discard)

        new_count = await self.bot.honeypot_repo.increment_caught(message.channel.id)
        await self._refresh_counter(message.channel.id, new_count)
        await self._log_catch(member, message, trigger_content, duration)

    async def _schedule_unban(self, guild: discord.Guild, user_id: int, delay: int) -> None:
        await asyncio.sleep(delay)
        user = discord.Object(id=user_id)
        try:
            await guild.unban(user, reason="Honeypot softban expired (auto-unban).")
        except discord.NotFound:
            return  # Already unbanned / no longer banned.
        except discord.HTTPException as exc:
            log.warning("Failed to auto-unban %s: %s", user_id, exc)
            return

        if await self._dm_on_unban():
            await self._dm_user(guild, user_id)

    async def _dm_user(self, guild: discord.Guild, user_id: int) -> None:
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            await user.send(
                f"Heads up: your account triggered the security trap in **{guild.name}** "
                "and was temporarily removed because it looked compromised. "
                "If that was unexpected, please secure your account (change your password, "
                "enable 2FA) and you're welcome to rejoin."
            )
        except discord.HTTPException:
            pass  # DMs closed; nothing we can do.

    async def _refresh_counter(self, channel_id: int, count: int) -> None:
        record = await self.bot.honeypot_repo.get(channel_id)
        if record is None or record.embed_message_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            warning = await channel.fetch_message(record.embed_message_id)
            await warning.edit(view=HoneypotWarningView(count))
        except discord.HTTPException as exc:
            log.warning("Failed to refresh honeypot counter in #%s: %s", channel_id, exc)

    async def _log_catch(
        self,
        member: discord.Member,
        message: discord.Message,
        trigger_content: str,
        duration: int,
    ) -> None:
        channel_id = self.bot.config.mod_log_channel_id
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            return

        embed = branded_embed(title="\U0001f528 Honeypot Catch", color=DANGER)
        embed.add_field(name="Account", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Channel", value=f"<#{message.channel.id}>", inline=True)
        embed.add_field(name="Action", value=f"Softban \u2022 auto-unban in {duration}s", inline=True)
        embed.add_field(name="Purged window", value=f"{_PURGE_SECONDS // 3600}h of messages", inline=True)
        embed.add_field(name="Triggering message", value=trigger_content[:1024], inline=False)
        embed.timestamp = dt.datetime.now(dt.timezone.utc)
        embed.set_footer(text="The real owner may need a heads-up once recovered.")
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            log.warning("Failed to write honeypot mod-log: %s", exc)


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(Honeypot(bot))
