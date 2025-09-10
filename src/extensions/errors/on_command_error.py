from datetime import UTC, datetime, timedelta

from interactions import Client, Extension, SlashContext, Timestamp, TimestampStyles, listen
from interactions.api.events import CommandError
from interactions.client.errors import (
    BadArgument,
    CommandCheckFailure,
    CommandOnCooldown,
    MaxConcurrencyReached,
)

from src.common import Emoji


class OnCommandError(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot

    @listen(CommandError, disable_default_listeners=True)
    async def on_command_error(self, event: CommandError) -> None:
        if isinstance(event.error, CommandOnCooldown) and isinstance(event.ctx, SlashContext):
            cooldown_time = event.error.cooldown.get_cooldown_time()

            end_time = datetime.now(UTC) + timedelta(seconds=cooldown_time)
            end_timestamp = Timestamp.fromdatetime(end_time).format(TimestampStyles.RelativeTime)

            await event.ctx.send(
                f'⏳ Please wait {end_timestamp} more seconds!',
                delete_after=cooldown_time,
                ephemeral=True,
            )

        if isinstance(event.error, CommandCheckFailure) and isinstance(event.ctx, SlashContext):
            await event.ctx.send(
                f'{Emoji.WRONG} You do not have permission to run this command.',
                delete_after=10,
                ephemeral=True,
            )

        if isinstance(event.error, BadArgument) and isinstance(event.ctx, SlashContext):
            await event.ctx.send(
                f'{Emoji.WRONG} {event.error}',
                delete_after=10,
                ephemeral=True,
            )

        if isinstance(event.error, MaxConcurrencyReached) and isinstance(event.ctx, SlashContext):
            await event.ctx.send(
                f'{Emoji.WRONG} This command has reached its maximum concurrent usage.\nPlease try again shortly.',
                delete_after=10,
                ephemeral=True,
            )
