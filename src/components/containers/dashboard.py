from __future__ import annotations

from typing import List

from interactions import (
    ActionRow,
    Button,
    Client,
    ContainerComponent,
    SectionComponent,
    SeparatorComponent,
    SeparatorSpacingSize,
    StringSelectMenu,
    TextDisplayComponent,
    ThumbnailComponent,
)

from src.common import Colors


class DashboardContainer:
    def __init__(
        self,
        client: Client,
        *,
        faq_select_menu: StringSelectMenu,
        faq_accessory: Button | ThumbnailComponent,
        dashboard_update_button: Button,
    ) -> None:
        self._client = client
        self.faq_select_menu = faq_select_menu
        self.faq_accessory = faq_accessory
        self.dashboard_update_button = dashboard_update_button

    def build(self) -> List[ContainerComponent]:
        return [
            ContainerComponent(
                TextDisplayComponent(content=f'# Dashboard: {self._client.user.username}'),
                SeparatorComponent(divider=True, spacing=SeparatorSpacingSize.LARGE),
                SectionComponent(
                    components=[
                        TextDisplayComponent('## List of FAQs'),
                    ],
                    accessory=self.faq_accessory,
                ),
                ActionRow(self.faq_select_menu),
                SeparatorComponent(divider=True, spacing=SeparatorSpacingSize.SMALL),
                ActionRow(self.dashboard_update_button),
                SeparatorComponent(divider=True, spacing=SeparatorSpacingSize.SMALL),
                accent_color=Colors.PRIMARY,
            ),
        ]
