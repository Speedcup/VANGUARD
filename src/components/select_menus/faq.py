from typing import List

from interactions import StringSelectMenu, StringSelectOption


class FaqStringSelectMenu(StringSelectMenu):
    def __init__(self, options: List[StringSelectOption], disabled: bool = False) -> None:
        super().__init__(
            *options,
            placeholder='Select FAQ to edit...',
            custom_id='faq_string_select_menu',
            disabled=disabled,
        )
