from interactions import (
    Extension,
    listen,
    GuildText,
    Message,
    AuditLogEventType,
    Member,
    BaseMessage,
    Missing,
)
from interactions.api.events import MessageDelete


class Logging(Extension):
    message_log_channel: GuildText = None

    async def async_start(self):
        self.message_log_channel = await self.client.fetch_channel(
            channel_id=self.client.debug
            and "1275866594152812575"
            or "1287406640341057556"
        )

    @listen(MessageDelete)
    async def on_message_delete(self, event: MessageDelete):
        # raw_message = event.message

        message = event.message
        deleter: Member | None = None

        # This should support messages that aren't cached e.g. the bot has restarted, so we need to cache it first.
        # Does not work unfortunately, the message is deleted faster than I can cache it?
        # if isinstance(raw_message, BaseMessage):
        #     print("Message is not cached.")
        #     channel = await raw_message.guild.fetch_channel(channel_id=raw_message.channel.id)
        #     message = await channel.fetch_message(message_id=raw_message.id)
        # else:
        #     message = raw_message

        # If the message exists in our automod cache, we do not log it again, so we are removing it from our cache
        # thus this has been acknowledged and return.
        if not isinstance(
            self.client.internal_cache.find_automod_message_and_remove(message=message),
            Missing,
        ):
            return

        # If the message is an instance of BaseMessage then it was not cached, so we cannot process it any further so we are just coping with it and returning here.
        # Somehow _author_id is None, so we cannot even cache the member who deleted their message, this is also why we cannot even use AuditLog Events because the author id is necessary to check whose message got deleted.
        if not isinstance(message, Message):
            # content="<:icons_warning:1275889956442734686> This message was not cached, so we cannot show its content."
            return

        # If the user is a bot, don't log the deletion. Bots most likely send embeds etc, so this would fuck everything up.
        if message.author.bot:
            return

        if deletion_log := await message.guild.fetch_audit_log(
            action_type=AuditLogEventType.MESSAGE_DELETE, limit=1
        ):
            try:
                entry = deletion_log.entries[0]

                if entry.target_id == message.author.id:
                    deleter = self.client.get_user(
                        user_id=deletion_log.entries[0].user_id
                    )
            finally:
                pass

        raw_message_content = message.content.replace("```", "")
        content = f"```{raw_message_content}```" if len(raw_message_content) > 0 else ""
        # Get the attachment urls so it is logged what attachments were attached to that message.
        attachments = [attachment.url for attachment in message.attachments]

        await self.message_log_channel.send(
            content=deleter
            and f"Message by {message.author.mention} deleted by {deleter.mention} in {message.channel.mention}.\n{content}"
            + "\n".join(attachments)
            or f"Message by {message.author.mention} deleted by themselves in {message.channel.mention}.\n{content}"
            + "\n".join(attachments)
        )

        # await self.message_log_channel.send(
        #     content=deleter and
        #             f"{deleter.mention} has deleted {message.author.mention} message in {message.channel.mention}.\n{content}" or
        #             f"{message.author.mention} has deleted their message in {message.channel.mention}.\n{content}"
        # )
