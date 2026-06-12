"""Staff management of database-backed option sets.

Option sets are the single, generic source of truth for every select menu's
contents (iPhone models, iOS versions, suggestion categories, ...). Editing them
here changes the menus instantly with no code change or redeploy.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import VanguardBot
from ui.embeds import branded_embed
from utils.checks import staff_only

log = logging.getLogger("vanguard.cog.options")

_AUTOCOMPLETE_LIMIT = 25


class OptionSets(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot

    options = app_commands.Group(
        name="options",
        description="Manage select-menu option sets (staff only).",
    )

    # ------------------------------------------------------------------ #
    # Commands                                                            #
    # ------------------------------------------------------------------ #
    @options.command(name="add", description="Add an option to a set (creates the set if new).")
    @app_commands.describe(
        set_name="The option set (e.g. iphone_model)",
        label="Text shown to users",
        value="Stored value (defaults to the label)",
        description="Optional sub-text shown under the option in the menu",
        order="Display order (defaults to end of list)",
    )
    @staff_only()
    async def add(
        self,
        interaction: discord.Interaction,
        set_name: str,
        label: str,
        value: str | None = None,
        description: str | None = None,
        order: int | None = None,
    ) -> None:
        item = await self.bot.option_sets_repo.add(
            set_name=set_name,
            label=label,
            value=value or label,
            description=description,
            display_order=order,
        )
        if item is None:
            await interaction.response.send_message(
                f"\u26a0\ufe0f `{value or label}` already exists in `{set_name}`.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"\u2705 Added **{item.label}** to `{set_name}` (order {item.display_order}).",
            ephemeral=True,
        )

    @options.command(name="edit", description="Edit an option's label, description and/or order.")
    @app_commands.describe(
        set_name="The option set",
        value="The value of the option to edit",
        label="New label (leave empty to keep)",
        description="New description shown under the option (leave empty to keep)",
        order="New display order (leave empty to keep)",
    )
    @staff_only()
    async def edit(
        self,
        interaction: discord.Interaction,
        set_name: str,
        value: str,
        label: str | None = None,
        description: str | None = None,
        order: int | None = None,
    ) -> None:
        if label is None and description is None and order is None:
            await interaction.response.send_message(
                "\u26a0\ufe0f Provide a new label, description and/or order.", ephemeral=True
            )
            return
        item = await self.bot.option_sets_repo.edit(
            set_name=set_name,
            value=value,
            label=label,
            description=description,
            display_order=order,
        )
        if item is None:
            await interaction.response.send_message(
                f"\u26a0\ufe0f No option `{value}` in `{set_name}`.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"\u2705 Updated `{value}` in `{set_name}`.", ephemeral=True
        )

    @options.command(name="disable", description="Disable an option (retire without deleting).")
    @app_commands.describe(set_name="The option set", value="The value to disable")
    @staff_only()
    async def disable(self, interaction: discord.Interaction, set_name: str, value: str) -> None:
        item = await self.bot.option_sets_repo.set_enabled(set_name, value, False)
        if item is None:
            await interaction.response.send_message(
                f"\u26a0\ufe0f No option `{value}` in `{set_name}`.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"\U0001f6ab Disabled **{item.label}** in `{set_name}`.", ephemeral=True
        )

    @options.command(name="enable", description="Re-enable a previously disabled option.")
    @app_commands.describe(set_name="The option set", value="The value to enable")
    @staff_only()
    async def enable(self, interaction: discord.Interaction, set_name: str, value: str) -> None:
        item = await self.bot.option_sets_repo.set_enabled(set_name, value, True)
        if item is None:
            await interaction.response.send_message(
                f"\u26a0\ufe0f No option `{value}` in `{set_name}`.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"\u2705 Enabled **{item.label}** in `{set_name}`.", ephemeral=True
        )

    @options.command(name="remove", description="Permanently delete an option from a set.")
    @app_commands.describe(set_name="The option set", value="The value to remove")
    @staff_only()
    async def remove(self, interaction: discord.Interaction, set_name: str, value: str) -> None:
        removed = await self.bot.option_sets_repo.remove(set_name, value)
        if not removed:
            await interaction.response.send_message(
                f"\u26a0\ufe0f No option `{value}` in `{set_name}`.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"\U0001f5d1\ufe0f Removed `{value}` from `{set_name}`.", ephemeral=True
        )

    @options.command(name="list", description="List the options in a set.")
    @app_commands.describe(set_name="The option set to list")
    @staff_only()
    async def list_options(self, interaction: discord.Interaction, set_name: str) -> None:
        items = await self.bot.option_sets_repo.items(set_name)
        if not items:
            await interaction.response.send_message(
                f"`{set_name}` has no options (or doesn't exist).", ephemeral=True
            )
            return

        enabled_marker = "\u2705"
        disabled_marker = "\U0001f6ab"
        lines = []
        for item in items:
            marker = enabled_marker if item.enabled else disabled_marker
            line = f"`{item.display_order:>3}` {marker} **{item.label}** \u2014 `{item.value}`"
            if item.description:
                line += f"\n\u2003\u21b3 *{item.description}*"
            lines.append(line)
        embed = branded_embed(
            title=f"Option set: {set_name}",
            description="\n".join(lines)[:4000],
        )
        embed.set_footer(text=f"{len(items)} option(s) \u2022 \u2705 enabled \u2022 \U0001f6ab disabled")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------ #
    # Autocomplete (shared across the commands above)                     #
    # ------------------------------------------------------------------ #
    @add.autocomplete("set_name")
    @edit.autocomplete("set_name")
    @disable.autocomplete("set_name")
    @enable.autocomplete("set_name")
    @remove.autocomplete("set_name")
    @list_options.autocomplete("set_name")
    async def _set_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        names = await self.bot.option_sets_repo.set_names()
        filtered = [name for name in names if current.lower() in name.lower()]
        return [
            app_commands.Choice(name=name, value=name)
            for name in filtered[:_AUTOCOMPLETE_LIMIT]
        ]

    @edit.autocomplete("value")
    @disable.autocomplete("value")
    @enable.autocomplete("value")
    @remove.autocomplete("value")
    async def _value_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        # The set_name the user already picked is available via the namespace.
        set_name = getattr(interaction.namespace, "set_name", None)
        if not set_name:
            return []
        items = await self.bot.option_sets_repo.items(set_name)
        filtered = [
            item
            for item in items
            if current.lower() in item.value.lower() or current.lower() in item.label.lower()
        ]
        return [
            app_commands.Choice(name=f"{item.label} ({item.value})"[:100], value=item.value)
            for item in filtered[:_AUTOCOMPLETE_LIMIT]
        ]


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(OptionSets(bot))
