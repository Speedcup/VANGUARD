"""A reusable select menu that reads its options live from an option set.

Discord limits a select menu to 25 options. When a set holds more than that, the
menu paginates: the last/first slots become "Next"/"Previous" sentinels that flip
the page in place instead of submitting a choice. The chosen value is remembered
across page flips, so a selection made on page 1 survives navigating to page 2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from repositories.option_sets_repo import OptionItem

if TYPE_CHECKING:
    from ui.forms_views import PreModalView

_PAGE_SIZE = 23  # leave room for prev/next sentinels within the 25-option cap.
_NEXT = "__next__"
_PREV = "__prev__"


def _build_options(
    items: list[OptionItem],
    page: int,
    chosen_value: str | None,
) -> list[discord.SelectOption]:
    start = page * _PAGE_SIZE
    window = items[start : start + _PAGE_SIZE]

    options: list[discord.SelectOption] = [
        discord.SelectOption(
            label=item.label[:100],
            value=item.value[:100],
            description=item.description[:100] if item.description else None,
            default=item.value == chosen_value,
        )
        for item in window
    ]

    if page > 0:
        options.insert(0, discord.SelectOption(label="\u25c0 Previous page", value=_PREV))
    if start + _PAGE_SIZE < len(items):
        options.append(discord.SelectOption(label="\u25b6 Next page", value=_NEXT))
    return options


class LiveOptionSelect(discord.ui.Select["PreModalView"]):
    """A single-choice select bound to one option set, with pagination."""

    def __init__(self, *, key: str, field_label: str, items: list[OptionItem]) -> None:
        self.key = key
        self.field_label = field_label
        self._items = items
        self._page = 0
        self.chosen_value: str | None = None
        self.chosen_label: str | None = None

        super().__init__(
            placeholder=f"Select {field_label}\u2026",
            min_values=1,
            max_values=1,
            options=_build_options(items, 0, None),
        )

    def _rerender(self) -> None:
        self.options = _build_options(self._items, self._page, self.chosen_value)
        if self.chosen_label:
            self.placeholder = f"{self.field_label}: {self.chosen_label}"

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]

        if value == _NEXT:
            self._page += 1
            self._rerender()
            await interaction.response.edit_message(view=self.view)
            return
        if value == _PREV:
            self._page = max(0, self._page - 1)
            self._rerender()
            await interaction.response.edit_message(view=self.view)
            return

        self.chosen_value = value
        match = next((item for item in self._items if item.value == value), None)
        self.chosen_label = match.label if match else value
        self._rerender()

        if self.view is not None:
            self.view.refresh_continue()
        await interaction.response.edit_message(view=self.view)
