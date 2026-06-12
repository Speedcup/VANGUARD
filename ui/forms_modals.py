"""Modal forms for Bug Report / Suggestion / Help submissions.

Discord modals allow at most 5 components and cannot contain select menus, so any
selectable data (iPhone model, iOS version, suggestion category) is gathered in a
pre-modal view (see ``ui.forms_views``) and carried in as ``selections``. The
text fields below are deliberately consolidated to stay within the 5-component
limit while still capturing the requested information.
"""

from __future__ import annotations

import logging

import discord

from ui.embeds import PRIMARY, SECONDARY, branded_embed

log = logging.getLogger("vanguard.forms")

# selections maps an option-set key -> (value, human-readable label).
Selections = dict[str, tuple[str, str]]


class _BaseReportModal(discord.ui.Modal):
    """Shared submit/post/error plumbing for all report modals."""

    accent: discord.Color = PRIMARY
    report_kind: str = "Report"
    # Every concrete modal defines a "Title" field; annotated here for typing only
    # (a bare annotation does not register a component).
    summary: discord.ui.TextInput

    def __init__(
        self,
        *,
        title: str,
        channel: "discord.TextChannel | discord.ForumChannel | None",
        selections: Selections | None = None,
    ) -> None:
        super().__init__(title=title, timeout=900)
        self.channel = channel
        self.selections: Selections = selections or {}

    def build_embed(self, user: discord.abc.User) -> discord.Embed:  # pragma: no cover - overridden
        raise NotImplementedError

    def thread_name(self) -> str:
        """Forum-post title for this submission (Discord caps thread names at 100)."""

        return f"{self.report_kind}: {self.summary.value}"[:100]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.channel is None:
            await interaction.response.send_message(
                "\u26a0\ufe0f This form isn't configured yet (no destination channel). "
                "Please let a staff member know.",
                ephemeral=True,
            )
            return

        embed = self.build_embed(interaction.user)
        try:
            if isinstance(self.channel, discord.ForumChannel):
                # Each submission becomes a new forum post (thread).
                await self.channel.create_thread(name=self.thread_name(), embed=embed)
            else:
                await self.channel.send(embed=embed)
        except discord.Forbidden:
            log.warning("Missing permission to post %s in %s", self.report_kind, self.channel)
            await interaction.response.send_message(
                "\u26a0\ufe0f I don't have permission to post your submission. "
                "Please let a staff member know.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as exc:
            log.warning("Failed to post %s submission: %s", self.report_kind, exc)
            await interaction.response.send_message(
                "\u26a0\ufe0f I couldn't post your submission. If the destination is a "
                "forum, it may require a tag to be selected. Please let a staff member know.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"\u2705 Your {self.report_kind.lower()} has been submitted. Thank you!",
            ephemeral=True,
        )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
    ) -> None:
        log.exception("Error handling %s modal submission: %s", self.report_kind, error)
        message = "\u26a0\ufe0f Something went wrong submitting your form. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class BugReportModal(_BaseReportModal):
    report_kind = "Bug Report"
    accent = PRIMARY

    summary = discord.ui.TextInput(
        label="Title",
        placeholder="A short summary of the bug",
        max_length=100,
        required=True,
    )
    app_version = discord.ui.TextInput(
        label="App Version",
        placeholder="e.g. 2.3.1",
        max_length=32,
        required=True,
    )
    description = discord.ui.TextInput(
        label="Bug Description",
        placeholder="What happens, and what did you expect instead?",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )
    steps = discord.ui.TextInput(
        label="Steps to Reproduce",
        placeholder="1. ...\n2. ...\n3. ...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )
    media = discord.ui.TextInput(
        label="Screenshots / Videos",
        placeholder="Paste links to screenshots or screen recordings",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )

    def build_embed(self, user: discord.abc.User) -> discord.Embed:
        embed = branded_embed(title=f"\U0001f41e Bug Report: {self.summary.value}", color=self.accent)
        model = self.selections.get("iphone_model", ("", "Not specified"))[1]
        line = self.selections.get("iphone_line", ("", "(Standard)"))[1]
        ios = self.selections.get("ios_version", ("", "Not specified"))[1]
        embed.add_field(name="iPhone Model", value=model, inline=True)
        embed.add_field(name="Line", value=line, inline=True)
        embed.add_field(name="iOS Version", value=ios, inline=True)
        embed.add_field(name="App Version", value=self.app_version.value, inline=True)
        embed.add_field(name="Description", value=self.description.value, inline=False)
        if self.steps.value:
            embed.add_field(name="Steps to Reproduce", value=self.steps.value, inline=False)
        if self.media.value:
            embed.add_field(name="Screenshots / Videos", value=self.media.value, inline=False)
        embed.set_footer(text=f"Submitted by {user} \u2022 {user.id}")
        return embed


class SuggestionModal(_BaseReportModal):
    report_kind = "Suggestion"
    accent = SECONDARY

    summary = discord.ui.TextInput(
        label="Title",
        placeholder="A short title for your suggestion",
        max_length=100,
        required=True,
    )
    suggestion = discord.ui.TextInput(
        label="Suggestion",
        placeholder="Describe your idea in detail",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )
    benefits = discord.ui.TextInput(
        label="Benefits",
        placeholder="How would this help users?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )
    mockups = discord.ui.TextInput(
        label="Mockups / Examples",
        placeholder="Links to mockups, references, or examples",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )

    def build_embed(self, user: discord.abc.User) -> discord.Embed:
        embed = branded_embed(title=f"\U0001f4a1 Suggestion: {self.summary.value}", color=self.accent)
        category = self.selections.get("suggestion_category", ("", "Uncategorised"))[1]
        embed.add_field(name="Category", value=category, inline=True)
        embed.add_field(name="Suggestion", value=self.suggestion.value, inline=False)
        if self.benefits.value:
            embed.add_field(name="Benefits", value=self.benefits.value, inline=False)
        if self.mockups.value:
            embed.add_field(name="Mockups / Examples", value=self.mockups.value, inline=False)
        embed.set_footer(text=f"Submitted by {user} \u2022 {user.id}")
        return embed


class HelpModal(_BaseReportModal):
    report_kind = "Help Request"
    accent = PRIMARY

    summary = discord.ui.TextInput(
        label="Title",
        placeholder="A short summary of what you need help with",
        max_length=100,
        required=True,
    )
    details = discord.ui.TextInput(
        label="Details",
        placeholder="Describe your issue or question",
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True,
    )
    media = discord.ui.TextInput(
        label="Screenshots",
        placeholder="Paste links to any helpful screenshots",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False,
    )

    def build_embed(self, user: discord.abc.User) -> discord.Embed:
        embed = branded_embed(title=f"\u2753 Help: {self.summary.value}", color=self.accent)
        embed.add_field(name="Details", value=self.details.value, inline=False)
        if self.media.value:
            embed.add_field(name="Screenshots", value=self.media.value, inline=False)
        embed.set_footer(text=f"Submitted by {user} \u2022 {user.id}")
        return embed
