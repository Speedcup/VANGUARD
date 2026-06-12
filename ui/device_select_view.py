"""The bug-report device-info step.

A polished, ephemeral view that gathers the reporter's device before the bug
modal opens. It collects four structured fields across independent selects:

* **iPhone model** — a flat list (see ``iphone_model`` option set).
* **Line / variant** — a separate selector (``iphone_line``), defaulting to
  "(Standard)" so owners of a non-variant phone aren't forced to pick.
* **iOS version** — gathered in two dependent steps (major, then minor) so each
  select stays well under Discord's 25-option cap even as point releases pile up.

The model/line selectors are intentionally **independent**: not every
combination is real (no "iPhone SE Pro"), but this is triage data we can clarify
later, so light filtering isn't worth the complexity. The embed restates the
running selection and explains where to find each value in iOS Settings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from repositories.option_sets_repo import OptionItem
from ui.embeds import PRIMARY, branded_embed
from ui.forms_modals import BugReportModal

if TYPE_CHECKING:
    from bot.client import VanguardBot

_NONE = "__none__"
_DASH = "\u2014"  # Kept out of f-string expressions (backslashes there break <3.12).
_DISCLAIMER = (
    "Collected only for triage \u2014 matching your report to the right device "
    "and OS. Nothing else."
)


def _major_of(version: str) -> str:
    return version.split(".", 1)[0]


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) if part.isdigit() else 0 for part in version.split("."))


class _ModelSelect(discord.ui.Select["DeviceSelectView"]):
    def __init__(self, models: list[OptionItem]) -> None:
        options = [
            discord.SelectOption(label=item.label[:100], value=item.value[:100])
            for item in models[:25]
        ]
        super().__init__(
            placeholder="Select your iPhone model\u2026",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        view.model_value = self.values[0]
        for option in self.options:
            option.default = option.value == self.values[0]
        view.model_label = next(
            (o.label for o in self.options if o.value == self.values[0]), self.values[0]
        )
        self.placeholder = f"Model: {view.model_label}"
        view.refresh()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class _LineSelect(discord.ui.Select["DeviceSelectView"]):
    def __init__(self, lines: list[OptionItem], default_value: str) -> None:
        options = [
            discord.SelectOption(
                label=item.label[:100],
                value=item.value[:100],
                description=item.description[:100] if item.description else None,
                default=item.value == default_value,
            )
            for item in lines[:25]
        ]
        super().__init__(
            placeholder="Line / variant \u2014 default: (Standard)",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        view.line_value = self.values[0]
        for option in self.options:
            option.default = option.value == self.values[0]
        view.line_label = next(
            (o.label for o in self.options if o.value == self.values[0]), self.values[0]
        )
        view.refresh()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class _IosMajorSelect(discord.ui.Select["DeviceSelectView"]):
    def __init__(self, majors: list[str]) -> None:
        options = [discord.SelectOption(label=f"iOS {major}", value=major) for major in majors[:25]]
        super().__init__(
            placeholder="iOS version \u2014 pick the major release\u2026",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        major = self.values[0]
        for option in self.options:
            option.default = option.value == major
        self.placeholder = f"iOS {major}.x"
        view.populate_minors(major)
        view.refresh()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class _IosMinorSelect(discord.ui.Select["DeviceSelectView"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Pick the major version first\u2026",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="\u2014", value=_NONE)],
            disabled=True,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        value = self.values[0]
        if value != _NONE:
            view.ios_value = value
            for option in self.options:
                option.default = option.value == value
            self.placeholder = f"iOS {value}"
            view.refresh()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class _ContinueButton(discord.ui.Button["DeviceSelectView"]):
    def __init__(self) -> None:
        super().__init__(label="Continue", style=discord.ButtonStyle.success, disabled=True)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        selections = {
            "iphone_model": (view.model_value or "", view.model_label or ""),
            "iphone_line": (view.line_value or "", view.line_label or ""),
            "ios_version": (view.ios_value or "", f"iOS {view.ios_value}"),
        }
        await interaction.response.send_modal(
            BugReportModal(title="Bug Report", channel=view.channel, selections=selections)
        )
        view.stop()


class DeviceSelectView(discord.ui.View):
    """Gathers model + line + iOS (major/minor) before opening the bug modal."""

    def __init__(
        self,
        *,
        channel: "discord.TextChannel | discord.ForumChannel | None",
        models: list[OptionItem],
        lines: list[OptionItem],
        ios_items: list[OptionItem],
        default_line_value: str = "standard",
    ) -> None:
        super().__init__(timeout=300)
        self.channel = channel
        self._ios_items = ios_items

        self.model_value: str | None = None
        self.model_label: str | None = None

        # The line defaults to "(Standard)" so non-variant owners can skip it.
        default_line = next(
            (item for item in lines if item.value == default_line_value),
            lines[0] if lines else None,
        )
        self.line_value: str | None = default_line.value if default_line else None
        self.line_label: str | None = default_line.label if default_line else None

        self.ios_value: str | None = None

        self._model_select = _ModelSelect(models)
        self.add_item(self._model_select)

        if lines:
            self.add_item(_LineSelect(lines, self.line_value or default_line_value))

        majors = sorted({_major_of(item.value) for item in ios_items}, key=int, reverse=True)
        self.add_item(_IosMajorSelect(majors))

        self._minor_select = _IosMinorSelect()
        self.add_item(self._minor_select)

        self._continue = _ContinueButton()
        self.add_item(self._continue)

    def populate_minors(self, major: str) -> None:
        minors = sorted(
            (item for item in self._ios_items if _major_of(item.value) == major),
            key=lambda item: _version_key(item.value),
        )
        self.ios_value = None
        if minors:
            self._minor_select.options = [
                discord.SelectOption(label=item.value[:100], value=item.value[:100])
                for item in minors
            ]
            self._minor_select.disabled = False
            self._minor_select.placeholder = "Select your exact iOS version\u2026"
        else:
            self._minor_select.options = [discord.SelectOption(label="\u2014", value=_NONE)]
            self._minor_select.disabled = True

    def refresh(self) -> None:
        self._continue.disabled = not (self.model_value and self.ios_value)

    def build_embed(self) -> discord.Embed:
        embed = branded_embed(
            title="\U0001f41e Report a Bug \u2014 Your Device",
            color=PRIMARY,
        )
        embed.description = (
            "Tell us what you're running so we can reproduce and triage your bug faster.\n\n"
            "**Where to find this** \u2014 open **Settings \u203a General \u203a About** on your iPhone:\n"
            "\u2003\u2022 **Model Name** \u2192 your iPhone model & line\n"
            "\u2003\u2022 **Software Version** \u2192 your iOS version\n\n"
            "Make each selection below, then press **Continue** to open the form."
        )
        ios_display = f"iOS {self.ios_value}" if self.ios_value else _DASH
        embed.add_field(
            name="\U0001f4f1 Your selection",
            value=(
                f"**Model:** {self.model_label or _DASH}\n"
                f"**Line:** {self.line_label or '(Standard)'}\n"
                f"**iOS:** {ios_display}"
            ),
            inline=False,
        )
        embed.set_footer(text=_DISCLAIMER)
        return embed


async def start_device_flow(
    bot: "VanguardBot",
    interaction: discord.Interaction,
    channel: "discord.TextChannel | discord.ForumChannel | None",
) -> None:
    """Open the device-info step, or fall back to the modal if data is missing."""

    models = await bot.option_sets_repo.items("iphone_model", enabled_only=True)
    lines = await bot.option_sets_repo.items("iphone_line", enabled_only=True)
    ios_items = await bot.option_sets_repo.items("ios_version", enabled_only=True)

    if not models or not ios_items:
        await interaction.response.send_modal(
            BugReportModal(title="Bug Report", channel=channel, selections={})
        )
        return

    view = DeviceSelectView(channel=channel, models=models, lines=lines, ios_items=ios_items)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)
