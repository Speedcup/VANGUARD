import logging

from interactions import ChannelType, Client, Extension, listen
from interactions.api.events import MessageCreate

from src.common import Emoji, env
from src.utils import Embed, LanguageCheckResult, LanguageDetector, LanguageLevel


class OnMessageCreate(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.detector = LanguageDetector()

    @listen(MessageCreate)
    async def on_message_create(self, event: MessageCreate) -> None:
        msg = event.message
        msg_delete_log_channel = await self.bot.fetch_channel(env.bot.msg_delete_log_channel)

        if msg.author.bot:
            return

        if msg.channel.type == ChannelType.GUILD_NEWS:
            await msg.publish()
            await msg.add_reaction(Emoji.MEGA)

        if not msg.content or not msg.content.strip():
            return

        if msg.channel.id in env.bot.whitelist_channels:
            return

        if msg.content and msg.content.strip():
            try:
                result: LanguageCheckResult = await self.detector.detect(msg.content)

                if result.language == LanguageLevel.NON_ENGLISH:
                    logging.warning(
                        f'Non-English message blocked | User: {msg.author.tag} | Msg: {msg.content[:100]}...'
                    )

                    await msg.delete()

                    await msg.channel.send(
                        content=f'{msg.author.mention} ⚠️ Your message was removed because it contains text in a language other than English. '
                        'This server uses English as the primary language for communication.',
                        delete_after=10,
                    )

                    if msg_delete_log_channel:
                        embed = Embed(
                            title='🚫 Non-English Message Blocked',
                            description=f'Message from {msg.author.mention} was deleted.',
                        )
                        embed.add_field(
                            name='User',
                            value=f'`{msg.author.tag}` (`{msg.author.id}`)',
                            inline=False,
                        )
                        embed.add_field(name='Channel', value=f'<#{msg.channel.id}>', inline=False)
                        embed.add_field(
                            name='Category', value=f'`{msg.channel.parent_id}`', inline=False
                        )
                        embed.add_field(
                            name='Reason', value=f'```{result.reason}```', inline=False
                        )
                        embed.add_field(
                            name='Message Content',
                            value=f'> {msg.content[:1000]}{"..." if len(msg.content) > 1000 else ""}',
                            inline=False,
                        )

                        await msg_delete_log_channel.send(embed=embed)

            except Exception as e:
                logging.error(f'Failed to check language for message {msg.id}: {e}')

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.detector.close()
