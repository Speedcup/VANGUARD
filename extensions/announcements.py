from interactions import Extension, listen, ChannelType
from interactions.api.events import MessageCreate


class Announcements(Extension):
    @listen(MessageCreate)
    async def on_message(self, event: MessageCreate):
        message = event.message

        if message.channel.type == ChannelType.GUILD_NEWS:
            await message.publish()
            await message.add_reaction(":mega:")
