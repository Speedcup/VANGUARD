from interactions import (
    AutocompleteContext,
    Buckets,
    Client,
    Extension,
    Message,
    OptionType,
    SlashContext,
    cooldown,
    slash_command,
    slash_option,
)

from src.common import env
from src.database import FaqController
from src.utils import Embed


class Faq(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.faq_controller = FaqController()
        self.embed = Embed()

    @cooldown(Buckets.USER, rate=env.bot.rate_cooldown, interval=env.bot.interval_cooldown)
    @slash_command(name='faq', description='Frequently Asked Questions')
    @slash_option(
        name='option',
        description='Choose the topic of the question.',
        required=True,
        opt_type=OptionType.STRING,
        autocomplete=True,
    )
    async def on_faq(self, ctx: SlashContext, option: str) -> Message:
        get_faq = await self.faq_controller.get_by_id(option)

        if get_faq:
            self.embed.title = get_faq.title
            self.embed.description = get_faq.description

            return await ctx.send(embed=self.embed)

        return await ctx.send(
            content=f"I didn't find anything for the query: `{option}`",
            ephemeral=True,
            delete_after=10,
        )

    @on_faq.autocomplete('option')
    async def on_faq_autocomplete(self, ctx: AutocompleteContext) -> None:
        input_text = ctx.input_text or ''

        get_all_faqs = await self.faq_controller.get_all()

        if not get_all_faqs:
            return await ctx.send(choices=[])

        filtered = [faq for faq in get_all_faqs if input_text.lower() in faq.id.lower()]

        choices = [{'name': faq.id, 'value': faq.id} for faq in filtered[:25]]

        return await ctx.send(choices=choices)
