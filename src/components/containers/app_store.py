from datetime import datetime
from typing import List

from interactions import (
    ContainerComponent,
    SectionComponent,
    SeparatorComponent,
    SeparatorSpacingSize,
    TextDisplayComponent,
    ThumbnailComponent,
    Timestamp,
    TimestampStyles,
    UnfurledMediaItem,
)

from src.common import VALPAW_LOGO, Colors, Emoji, env


class AppStoreContainer:
    def __init__(self, version: str, release_notes: str, release_date: datetime) -> None:
        self.version = version
        self.release_notes = release_notes
        self.release_date = release_date

    def build(self) -> List[ContainerComponent]:
        return [
            ContainerComponent(
                SectionComponent(
                    components=[
                        TextDisplayComponent(f'# New release: v{self.version}'),
                    ],
                    accessory=ThumbnailComponent(media=UnfurledMediaItem(url=VALPAW_LOGO)),
                ),
                SeparatorComponent(divider=True, spacing=SeparatorSpacingSize.SMALL),
                TextDisplayComponent(f'{self.release_notes}\n\n<@&{env.bot.app_store_role}>'),
                SeparatorComponent(divider=True, spacing=SeparatorSpacingSize.LARGE),
                TextDisplayComponent(
                    f'{Emoji.APP_STORE} **Provided by App Store** •'
                    f' {Timestamp.format(self.release_date, TimestampStyles.LongDateTime)}'
                    f' • {Timestamp.format(self.release_date, TimestampStyles.RelativeTime)}'
                ),
                accent_color=Colors.PRIMARY,
            ),
        ]
