"""Views powering the modal-form entry points.

Two entry points open the same flows: a persistent button panel
(``FormsEntryView``) and slash commands. Because modals can't hold select menus,
flows that need selectable data first show a ``PreModalView`` (the live option
selects + a Continue button) and only then open the modal, carrying the
selections in.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

import discord

from ui.device_select_view import start_device_flow
from ui.forms_modals import (
    HelpModal,
    Selections,
    SuggestionModal,
    _BaseReportModal,
)
from ui.option_select import LiveOptionSelect

if TYPE_CHECKING:
    from bot.client import VanguardBot

log = logging.getLogger("vanguard.forms")

ModalFactory = Callable[[Selections], _BaseReportModal]


class _ContinueButton(discord.ui.Button["PreModalView"]):
    def __init__(self) -> None:
        super().__init__(label="Continue", style=discord.ButtonStyle.success, disabled=True)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        selections: Selections = {
            select.key: (select.chosen_value or "", select.chosen_label or "")
            for select in view.selects
        }
        await interaction.response.send_modal(view.modal_factory(selections))
        view.stop()


class PreModalView(discord.ui.View):
    """Ephemeral view that collects select-menu choices before opening a modal."""

    def __init__(self, *, selects: list[LiveOptionSelect], modal_factory: ModalFactory) -> None:
        super().__init__(timeout=300)
        self.selects = selects
        self.modal_factory = modal_factory
        for select in selects:
            self.add_item(select)
        self._continue = _ContinueButton()
        self.add_item(self._continue)
        self.refresh_continue()

    def refresh_continue(self) -> None:
        self._continue.disabled = not all(select.chosen_value for select in self.selects)


async def _build_selects(
    bot: "VanguardBot",
    specs: list[tuple[str, str]],
) -> list[LiveOptionSelect]:
    """Create selects for each (set_name, field_label) that has enabled options."""

    selects: list[LiveOptionSelect] = []
    for set_name, field_label in specs:
        items = await bot.option_sets_repo.items(set_name, enabled_only=True)
        if items:
            selects.append(LiveOptionSelect(key=set_name, field_label=field_label, items=items))
    return selects


def _resolve_channel(
    bot: "VanguardBot", kind: str
) -> "discord.TextChannel | discord.ForumChannel | None":
    mapping = {
        "bug": bot.config.bug_channel,
        "suggestion": bot.config.suggestion_channel,
        "help": bot.config.help_channel,
    }
    channel_id = mapping.get(kind)
    if channel_id is None:
        return None
    channel = bot.get_channel(channel_id)
    # Submissions post to either a text channel (message) or a forum (new post).
    if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
        return channel
    return None


async def start_form_flow(bot: "VanguardBot", interaction: discord.Interaction, kind: str) -> None:
    """Shared entry point used by both the button panel and the slash commands."""

    channel = _resolve_channel(bot, kind)

    if kind == "help":
        await interaction.response.send_modal(HelpModal(title="Help Request", channel=channel))
        return

    if kind == "bug":
        # The bug flow has its own purpose-built, polished device-info step.
        await start_device_flow(bot, interaction, channel)
        return

    # suggestion
    specs = [("suggestion_category", "Category")]
    factory: ModalFactory = lambda s: SuggestionModal(  # noqa: E731
        title="Suggestion", channel=channel, selections=s
    )

    selects = await _build_selects(bot, specs)
    if not selects:
        # No selectable data configured; skip straight to the modal.
        await interaction.response.send_modal(factory({}))
        return

    view = PreModalView(selects=selects, modal_factory=factory)
    await interaction.response.send_message(
        "Select the options below, then press **Continue** to open the form.",
        view=view,
        ephemeral=True,
    )


class FormsEntryView(discord.ui.View):
    """Persistent button panel; registered in setup_hook so it survives restarts."""

    def __init__(self, bot: "VanguardBot") -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Report a Bug",
        style=discord.ButtonStyle.danger,
        emoji="\U0001f41e",
        custom_id="forms:bug",
    )
    async def bug_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await start_form_flow(self.bot, interaction, "bug")

    @discord.ui.button(
        label="Suggest an Idea",
        style=discord.ButtonStyle.primary,
        emoji="\U0001f4a1",
        custom_id="forms:suggestion",
    )
    async def suggestion_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await start_form_flow(self.bot, interaction, "suggestion")

    @discord.ui.button(
        label="Get Help",
        style=discord.ButtonStyle.secondary,
        emoji="\u2753",
        custom_id="forms:help",
    )
    async def help_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await start_form_flow(self.bot, interaction, "help")
