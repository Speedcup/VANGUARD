"""Centralised application-command error handling."""

from __future__ import annotations

import logging
from typing import Any

import discord
from discord import app_commands

from utils.checks import NotStaff

log = logging.getLogger("vanguard.errors")


class ErrorLog:
    """Generate memorable error codes and prefix console logs with them."""

    _DEFAULT_CODE = "panini"
    _CODE_BY_TYPE: dict[type[BaseException], str] = {
        NotStaff: "sushi",
        app_commands.CommandOnCooldown: "pizza",
        app_commands.CheckFailure: "taco",
        discord.Forbidden: "soup",
        discord.HTTPException: "waffle",
        Exception: _DEFAULT_CODE,
    }

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or log

    def make_code(self, error: object | None = None) -> str:
        """Return the code associated with an error type."""

        if hasattr(error, "original"):
            original = getattr(error, "original")
            if isinstance(original, BaseException):
                error = original

        if isinstance(error, BaseException):
            for error_type, code in self._CODE_BY_TYPE.items():
                if isinstance(error, error_type):
                    return code

        return self._DEFAULT_CODE

    def log_error(
        self,
        error: object | None,
        message: str,
        *args: object,
        level: int = logging.ERROR,
        exc_info: bool | BaseException | tuple[Any, Any, Any] = False,
    ) -> str:
        """Write a prefixed log line and return the error code that was used."""

        error_code = self.make_code(error)
        if isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
        self._logger.log(level, f"[%s] {message}", error_code, *args, exc_info=exc_info)
        return error_code


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
    error_log = ErrorLog()
    code = error_log.log_error(
        original,
        "Unhandled error in command %r: %s",
        command,
        original,
        exc_info=original,
    )

    await _respond(
        interaction,
        "\u26a0\ufe0f Something went wrong while running that command. "
        f"The error has been logged. Error code: `{code}`.",
    )
