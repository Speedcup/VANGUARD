from interactions import (
    Client,
    ComponentContext,
    Extension,
    StringSelectOption,
    component_callback,
)

from src.components import (
    DashboardContainer,
    DashboardUpdateButton,
    FaqCreateButton,
    FaqStringSelectMenu,
)
from src.database import FaqController


class DashboardButtonCallback(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.container = DashboardContainer
        self.select_menu = FaqStringSelectMenu
        self.faq_create_button = FaqCreateButton()
        self.faq_controller = FaqController()
        self.dashboard_update_button = DashboardUpdateButton()

    @component_callback('update_dashboard_button')
    async def dashboard_update_button_callback(self, ctx: ComponentContext) -> None:
        await ctx.defer(edit_origin=True)

        get_all_faq = await self.faq_controller.get_all()

        if not get_all_faq:
            options = [
                StringSelectOption(
                    label='Note FAQ',
                    value='none',
                )
            ]

            disabled = True
        else:
            options = [
                StringSelectOption(
                    label=f'{faq.id}',
                    value=str(faq.id),
                )
                for faq in get_all_faq
            ]

            disabled = False

        components = self.container(
            self.bot,
            faq_select_menu=self.select_menu(options, disabled),
            faq_accessory=self.faq_create_button,
            dashboard_update_button=self.dashboard_update_button,
        ).build()

        await ctx.message.edit(components=components)
