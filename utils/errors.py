"""Centralised application-command error handling."""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from utils.checks import NotStaff

log = logging.getLogger("vanguard.errors")


async def _respond(interaction: discord.Interaction, message: str) -> None:
    """Send an ephemeral error message, regardless of response state."""

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Global handler attached to the command tree."""

    if isinstance(error, NotStaff):
        await _respond(interaction, f"\u26d4 {error}")
        return

    if isinstance(error, app_commands.CheckFailure):
        await _respond(interaction, "\u26d4 You can't use this command here.")
        return

    if isinstance(error, app_commands.CommandOnCooldown):
        await _respond(
            interaction,
            f"\u23f3 Slow down \u2014 try again in {error.retry_after:.0f}s.",
        )
        return

    # Unwrap the underlying exception for cleaner logs.
    original = getattr(error, "original", error)
    command = interaction.command.qualified_name if interaction.command else "unknown"
    log.exception("Unhandled error in command %r: %s", command, original)

    await _respond(
        interaction,
        "\u26a0\ufe0f Something went wrong while running that command. "
        "The error has been logged.",
    )
