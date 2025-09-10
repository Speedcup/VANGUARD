from interactions import Button, ButtonStyle

from src.common import Emoji


class AppStoreButton(Button):
    def __init__(self) -> None:
        super().__init__(
            style=ButtonStyle.URL,
            label='App Store',
            emoji=Emoji.APP_STORE,
            url='https://apps.apple.com/app/id6476132885?action=write-review',
        )
