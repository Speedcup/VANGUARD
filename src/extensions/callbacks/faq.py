from interactions import (
    Client,
    ComponentContext,
    Extension,
    Message,
    ModalContext,
    component_callback,
    modal_callback,
)

from src.common import EDIT_FAQ_MODAL_CUSTOM_ID_PATTERN
from src.components import FaqCreateActionButton, FaqEditActionButton
from src.database import FaqController
from src.modals import FaqCreateModal, FaqEditModal
from src.utils import Embed


class FaqButtonCallback(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.faq_create_modal = FaqCreateModal
        self.faq_edit_modal = FaqEditModal
        self.faq_controller = FaqController()

    @component_callback('create_faq_button')
    async def create_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.send_modal(self.faq_create_modal())

    @component_callback('yes_create_faq_button')
    async def yes_create_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()

        embed = ctx.message.embeds[0]
        id_value = embed.footer.text.split('ID: ')[1]
        title_value = embed.title
        description_value = embed.description
        await self.faq_controller.create(id_value, title_value, description_value)

        await ctx.send(content='Frequently asked question successfully created!', delete_after=10)

    @component_callback('fix_create_faq_button')
    async def fix_create_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()

        embed = ctx.message.embeds[0]
        id_value = embed.footer.text.split('ID: ')[1]
        title_value = embed.title
        description_value = embed.description

        await ctx.send_modal(self.faq_create_modal(id_value, title_value, description_value))

    @component_callback('no_create_faq_button')
    async def no_create_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()
        await ctx.send(content='Creation of FAQ cancelled.', delete_after=10)

    @component_callback('start_edit_faq_button')
    async def start_edit_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()

        embed = ctx.message.embeds[0]
        id_value = embed.footer.text.split('ID: ')[1]
        title_value = embed.title
        description_value = embed.description

        await ctx.send_modal(self.faq_edit_modal(id_value, title_value, description_value))

    @component_callback('delete_faq_button')
    async def delete_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()

        embed = ctx.message.embeds[0]
        id_value = embed.footer.text.split('ID: ')[1]
        await self.faq_controller.delete(id_value)

        await ctx.send(content=f'FAQ `{id_value}` successfully deleted.', delete_after=10)

    @component_callback('cancel_edit_faq_button')
    async def cancel_edit_faq_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.message.delete()
        await ctx.send(content='Edition of FAQ cancelled.', delete_after=10)


class FaqModalCallback(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.faq_create_action_button = FaqCreateActionButton()
        self.faq_controller = FaqController()

    @modal_callback('create_faq_modal')
    async def create_faq_modal_callback(
        self, ctx: ModalContext, id_faq: str, title: str, description: str
    ) -> None:
        embed = Embed()
        embed.title = title
        embed.description = description
        embed.set_footer(text=f'ID: {id_faq}')

        await ctx.send(embed=embed, components=self.faq_create_action_button)

    @modal_callback(EDIT_FAQ_MODAL_CUSTOM_ID_PATTERN)
    async def edit_faq_modal_callback(
        self, ctx: ModalContext, title: str, description: str
    ) -> None:
        match = EDIT_FAQ_MODAL_CUSTOM_ID_PATTERN.match(ctx.custom_id)

        if match:
            custom_id = match.group(1)

            await self.faq_controller.update(custom_id, title, description)

            await ctx.send(content='Frequently asked question successfully edit!', delete_after=10)


class FaqSelectMenuCallback(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.faq_controller = FaqController()
        self.faq_edit_action_button = FaqEditActionButton()

    @component_callback('faq_string_select_menu')
    async def faq_string_select_menu_callback(self, ctx: ComponentContext) -> Message:
        get_faq = await self.faq_controller.get_by_id(ctx.values[0])

        if not get_faq:
            return await ctx.send(
                content=f"Strange, I didn't find anything for the query `{ctx.values}`"
            )

        embed = Embed()
        embed.title = get_faq.title
        embed.description = get_faq.description
        embed.set_footer(text=f'ID: {get_faq.id}')

        return await ctx.send(embed=embed, components=self.faq_edit_action_button)
