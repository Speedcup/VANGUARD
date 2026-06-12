"""Interactive FAQ administration panel.

A single ephemeral panel shows one FAQ entry at a time with a select menu to pick
the entry and buttons to modify the answer, edit the question/category, delete the
entry, or create a new one.

The Modify flow is deliberately reply-based: pressing Modify posts a normal
channel message and persists the (message -> entry, admin) link in the
``faq_edit_prompts`` table. The FAQ cog's ``on_message`` listener watches for a
reply to that message by the same admin and copies the reply's raw content
verbatim into the answer. That linkage is the entire state mechanism, so it works
across restarts with no in-memory timer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord

from repositories.faq_repo import FaqEntry
from ui.embeds import branded_embed

if TYPE_CHECKING:
    from bot.client import VanguardBot

log = logging.getLogger("vanguard.faq_admin")

PENDING_ANSWER = "_(pending \u2014 reply to the prompt with the answer)_"

_PAGE_SIZE = 23
_NEXT = "__next__"
_PREV = "__prev__"


def _entry_embed(entry: FaqEntry | None, total: int) -> discord.Embed:
    if entry is None:
        return branded_embed(
            title="FAQ Admin",
            description="No FAQ entries yet. Use **New Entry** to create one.",
        )
    embed = branded_embed(title=entry.question, description=entry.answer[:4096])
    embed.add_field(name="Key", value=f"`{entry.key}`", inline=True)
    embed.add_field(name="Category", value=entry.category or "None", inline=True)
    embed.set_footer(text=f"{total} FAQ entr{'y' if total == 1 else 'ies'}")
    return embed


class _EntrySelect(discord.ui.Select["FaqAdminView"]):
    def __init__(self, entries: list[FaqEntry], page: int, selected_key: str | None) -> None:
        self._entries = entries
        self._page = page
        start = page * _PAGE_SIZE
        window = entries[start : start + _PAGE_SIZE]

        options: list[discord.SelectOption] = [
            discord.SelectOption(
                label=entry.question[:100],
                value=entry.key,
                description=(f"{entry.key}" + (f" \u2022 {entry.category}" if entry.category else ""))[:100],
                default=entry.key == selected_key,
            )
            for entry in window
        ]
        if page > 0:
            options.insert(0, discord.SelectOption(label="\u25c0 Previous page", value=_PREV))
        if start + _PAGE_SIZE < len(entries):
            options.append(discord.SelectOption(label="\u25b6 Next page", value=_NEXT))

        super().__init__(placeholder="Select an FAQ entry\u2026", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        value = self.values[0]
        if value == _NEXT:
            view.page += 1
            view.render()
            await interaction.response.edit_message(view=view)
            return
        if value == _PREV:
            view.page = max(0, view.page - 1)
            view.render()
            await interaction.response.edit_message(view=view)
            return

        view.selected_key = value
        view.render()
        await interaction.response.edit_message(embed=view.current_embed(), view=view)


class FaqAdminView(discord.ui.View):
    def __init__(self, bot: "VanguardBot", entries: list[FaqEntry], admin_id: int) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.entries = entries
        self.admin_id = admin_id
        self.page = 0
        self.confirming_delete = False
        self.selected_key: str | None = entries[0].key if entries else None
        self.message: discord.Message | None = None
        self.render()

    # -- helpers --------------------------------------------------------- #
    def _selected_entry(self) -> FaqEntry | None:
        if self.selected_key is None:
            return None
        return next((e for e in self.entries if e.key == self.selected_key), None)

    def current_embed(self) -> discord.Embed:
        return _entry_embed(self._selected_entry(), len(self.entries))

    async def reload(self) -> None:
        """Refresh entries from the DB and keep a sensible selection."""

        self.entries = await self.bot.faq_repo.all_entries()
        if self.selected_key not in {e.key for e in self.entries}:
            self.selected_key = self.entries[0].key if self.entries else None
        max_page = max(0, (len(self.entries) - 1) // _PAGE_SIZE)
        self.page = min(self.page, max_page)
        self.confirming_delete = False
        self.render()

    async def refresh_message(self) -> None:
        if self.message is not None:
            try:
                await self.message.edit(embed=self.current_embed(), view=self)
            except discord.HTTPException:
                pass

    def render(self) -> None:
        """Rebuild the view's components for the current state."""

        self.clear_items()

        if self.confirming_delete:
            self.add_item(_ConfirmDeleteButton())
            self.add_item(_CancelDeleteButton())
            return

        if self.entries:
            self.add_item(_EntrySelect(self.entries, self.page, self.selected_key))
            self.add_item(_ModifyButton(disabled=self.selected_key is None))
            self.add_item(_EditDetailsButton(disabled=self.selected_key is None))
            self.add_item(_DeleteButton(disabled=self.selected_key is None))
        self.add_item(_NewEntryButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                "This panel belongs to another admin. Run `/faqadmin` yourself.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message is not None:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


# ---------------------------------------------------------------------- #
# Buttons                                                                 #
# ---------------------------------------------------------------------- #
class _ModifyButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self, disabled: bool) -> None:
        super().__init__(label="Modify Answer", style=discord.ButtonStyle.primary, disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        entry = view._selected_entry()
        if entry is None:
            await interaction.response.send_message("No entry selected.", ephemeral=True)
            return
        await _start_answer_prompt(view, interaction, entry.key)


class _EditDetailsButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self, disabled: bool) -> None:
        super().__init__(label="Edit Details", style=discord.ButtonStyle.secondary, disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        entry = view._selected_entry()
        if entry is None:
            await interaction.response.send_message("No entry selected.", ephemeral=True)
            return
        await interaction.response.send_modal(EditDetailsModal(view, entry))


class _DeleteButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self, disabled: bool) -> None:
        super().__init__(label="Delete", style=discord.ButtonStyle.danger, disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        view.confirming_delete = True
        view.render()
        entry = view._selected_entry()
        name = entry.key if entry else "this entry"
        embed = view.current_embed()
        embed.add_field(
            name="\u26a0\ufe0f Confirm deletion",
            value=f"Permanently delete **{name}**? This cannot be undone.",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class _ConfirmDeleteButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self) -> None:
        super().__init__(label="Confirm Delete", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        key = view.selected_key
        if key is not None:
            await view.bot.faq_repo.delete(key)
        await view.reload()
        await interaction.response.edit_message(embed=view.current_embed(), view=view)


class _CancelDeleteButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self) -> None:
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        view.confirming_delete = False
        view.render()
        await interaction.response.edit_message(embed=view.current_embed(), view=view)


class _NewEntryButton(discord.ui.Button["FaqAdminView"]):
    def __init__(self) -> None:
        super().__init__(label="New Entry", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        assert view is not None
        await interaction.response.send_modal(NewEntryModal(view))


# ---------------------------------------------------------------------- #
# Reply-prompt helper                                                     #
# ---------------------------------------------------------------------- #
async def _start_answer_prompt(view: "FaqAdminView", interaction: discord.Interaction, key: str) -> None:
    """Post the public 'reply with the answer' prompt and persist the linkage."""

    channel = interaction.channel
    if not isinstance(channel, discord.abc.Messageable):
        await interaction.response.send_message(
            "I can't post the reply prompt in this channel.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        "Posted a prompt below \u2014 **reply to it** with the new answer "
        "(formatting is copied verbatim).",
        ephemeral=True,
    )
    prompt = await channel.send(
        f"You are going to modify the following FAQ entry: **{key}**.\n\n"
        "Reply to this message with the new answer."
    )
    await view.bot.faq_repo.create_edit_prompt(
        prompt_message_id=prompt.id,
        channel_id=prompt.channel.id,
        faq_key=key,
        admin_id=interaction.user.id,
    )


# ---------------------------------------------------------------------- #
# Modals                                                                  #
# ---------------------------------------------------------------------- #
class NewEntryModal(discord.ui.Modal, title="New FAQ Entry"):
    key = discord.ui.TextInput(
        label="Key",
        placeholder="Unique short identifier, e.g. 'security'",
        max_length=64,
        required=True,
    )
    question = discord.ui.TextInput(
        label="Question",
        placeholder="The question this entry answers",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True,
    )
    category = discord.ui.TextInput(
        label="Category",
        placeholder="Optional category label",
        max_length=64,
        required=False,
    )

    def __init__(self, view: "FaqAdminView") -> None:
        super().__init__()
        self._view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot = self._view.bot
        key = self.key.value.strip()

        if await bot.faq_repo.get_by_key(key) is not None:
            await interaction.response.send_message(
                f"\u26a0\ufe0f An FAQ entry with key `{key}` already exists.", ephemeral=True
            )
            return

        embedding = await bot.embedder.encode(self.question.value)
        await bot.faq_repo.create(
            key=key,
            question=self.question.value,
            answer=PENDING_ANSWER,
            category=self.category.value.strip() or None,
            embedding=embedding,
        )
        await self._view.reload()
        self._view.selected_key = key
        self._view.render()
        await self._view.refresh_message()
        # Immediately open the reply-prompt for the answer (reuses the Modify flow).
        await _start_answer_prompt(self._view, interaction, key)


class EditDetailsModal(discord.ui.Modal, title="Edit FAQ Details"):
    def __init__(self, view: "FaqAdminView", entry: FaqEntry) -> None:
        super().__init__()
        self._view = view
        self._entry = entry
        self.question = discord.ui.TextInput(
            label="Question",
            default=entry.question,
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )
        self.category = discord.ui.TextInput(
            label="Category",
            default=entry.category or "",
            max_length=64,
            required=False,
        )
        self.add_item(self.question)
        self.add_item(self.category)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot = self._view.bot
        # Re-embed because the question (the matched text) may have changed.
        embedding = await bot.embedder.encode(self.question.value)
        await bot.faq_repo.update(
            key=self._entry.key,
            question=self.question.value,
            answer=self._entry.answer,
            category=self.category.value.strip() or None,
            embedding=embedding,
        )
        await self._view.reload()
        await interaction.response.send_message(
            f"\u2705 Updated details for `{self._entry.key}`.", ephemeral=True
        )
        await self._view.refresh_message()
