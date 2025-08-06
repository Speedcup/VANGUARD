from interactions import Buckets, Client, Extension, SlashContext, cooldown, slash_command

from src.common import env
from src.components import AppStoreButton
from src.utils import rate_app_embed


class RateApp(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.rate_app_embed = rate_app_embed()
        self.app_store_button = AppStoreButton()

    @cooldown(Buckets.USER, rate=env.bot.rate_cooldown, interval=env.bot.interval_cooldown)
    @slash_command(name='rate_app', description='Get a link to rate the app on the app store!')
    async def on_rate_app(
        self,
        ctx: SlashContext,
    ) -> None:
        await ctx.send(embed=self.rate_app_embed, components=self.app_store_button, ephemeral=True)
