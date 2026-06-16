"""Modal forms: Bug Report / Suggestion / Help.

Each form has two entry points: the persistent button panel posted by staff and a
slash command. Both route through ``start_form_flow``.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.client import VanguardBot
from ui.embeds import branded_embed
from ui.forms_views import FormsEntryView, start_form_flow
from utils.checks import staff_only

log = logging.getLogger("vanguard.cog.forms")


class Forms(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------ #
    # Slash entry points                                                  #
    # ------------------------------------------------------------------ #
    @app_commands.command(name="bugreport", description="Report a bug in the app.")
    async def bugreport(self, interaction: discord.Interaction) -> None:
        await start_form_flow(self.bot, interaction, "bug")

    @app_commands.command(name="suggest", description="Suggest a feature or improvement.")
    async def suggest(self, interaction: discord.Interaction) -> None:
        await start_form_flow(self.bot, interaction, "suggestion")

    @app_commands.command(name="help", description="Ask the team for help.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        await start_form_flow(self.bot, interaction, "help")

    # ------------------------------------------------------------------ #
    # Staff: post the persistent button panel                             #
    # ------------------------------------------------------------------ #
    @app_commands.command(name="forms_panel", description="Post the bug/suggestion/help panel here.")
    @app_commands.describe(channel="Channel to post the panel in (defaults to here)")
    @staff_only()
    async def forms_panel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            await interaction.response.send_message(
                "\u26a0\ufe0f I can't post in that channel.", ephemeral=True
            )
            return

        embed = branded_embed(
            title="\U0001f4ec Get in Touch",
            description=(
                "Use the buttons below to reach the team:\n\n"
                "\U0001f41e **Report a Bug** \u2014 something isn't working right.\n"
                "\U0001f4a1 **Suggest an Idea** \u2014 a feature or improvement.\n"
                "\u2753 **Get Help** \u2014 a question or issue you need a hand with."
            ),
        )
        await target.send(embed=embed, view=FormsEntryView(self.bot))
        await interaction.response.send_message(
            f"\u2705 Panel posted in {target.mention}.", ephemeral=True
        )


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(Forms(bot))
