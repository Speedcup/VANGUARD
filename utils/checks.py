"""Reusable application-command checks."""

from __future__ import annotations

import discord
from discord import app_commands


class NotStaff(app_commands.CheckFailure):
    """Raised when a non-staff user invokes a staff-gated command."""


def _is_staff_member(interaction: discord.Interaction) -> bool:
    member = interaction.user
    if not isinstance(member, discord.Member) or interaction.guild is None:
        return False

    if member.guild_permissions.administrator or member.id == interaction.guild.owner_id:
        return True

    staff_role_id = interaction.client.config.staff_role_id  # type: ignore[attr-defined]
    return any(role.id == staff_role_id for role in member.roles)


def staff_only():
    """Gate a command behind the configured staff role.

    Staff role members, the guild owner, and administrators pass. The role ID is
    read from the bot config at invocation time so it always reflects the live
    configuration.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        if _is_staff_member(interaction):
            return True
        raise NotStaff("You do not have permission to use this command.")

    return app_commands.check(predicate)
