from interactions import (
    Client,
    Extension,
    SlashContext,
    StringSelectOption,
    check,
    is_owner,
    slash_command,
)

from src.components import (
    DashboardContainer,
    DashboardUpdateButton,
    FaqCreateButton,
    FaqStringSelectMenu,
)
from src.database import FaqController


class Dashboard(Extension):
    def __init__(self, bot: Client) -> None:
        self.bot = bot
        self.container = DashboardContainer
        self.select_menu = FaqStringSelectMenu
        self.faq_create_button = FaqCreateButton()
        self.faq_controller = FaqController()
        self.dashboard_update_button = DashboardUpdateButton()

    @slash_command(
        name='dashboard', description='Bot dashboard, where you can perform certain actions.'
    )
    @check(is_owner())
    async def on_dashboard(self, ctx: SlashContext) -> None:
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

        await ctx.send(components=components)
