"""FAQ system: staff management, autocomplete retrieval, and an auto-responder.

The auto-responder listens to ordinary messages and, when one closely matches a
stored FAQ question, replies with the answer. Matching is two-stage (RapidFuzz
fast-path then pgvector semantic search) and deliberately conservative: it would
rather stay silent than answer wrongly.
"""

from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands
from rapidfuzz import fuzz, process

from bot.client import VanguardBot
from services.intent_classifier import Intent, classify
from ui.embeds import branded_embed
from ui.faq_admin_view import FaqAdminView
from utils.checks import staff_only

log = logging.getLogger("vanguard.cog.faq")

_AUTOCOMPLETE_LIMIT = 25


class FAQ(commands.Cog):
    def __init__(self, bot: VanguardBot) -> None:
        self.bot = bot
        # (channel_id, user_id) -> monotonic timestamp of last auto-response.
        self._cooldowns: dict[tuple[int, int], float] = {}
        # Separate bucket for intent nudges so they don't share the FAQ timer.
        self._nudge_cooldowns: dict[tuple[int, int], float] = {}

    # ------------------------------------------------------------------ #
    # Settings helpers                                                    #
    # ------------------------------------------------------------------ #
    async def _similarity_threshold(self) -> float:
        return await self.bot.settings_repo.get_float(
            "faq_similarity_threshold", self.bot.config.faq_similarity_threshold
        )

    async def _fuzzy_threshold(self) -> float:
        return await self.bot.settings_repo.get_float(
            "faq_fuzzy_threshold", self.bot.config.faq_fuzzy_threshold
        )

    async def _cooldown_seconds(self) -> int:
        return await self.bot.settings_repo.get_int(
            "faq_cooldown_seconds", self.bot.config.faq_cooldown_seconds
        )

    async def _min_message_length(self) -> int:
        return await self.bot.settings_repo.get_int(
            "faq_min_message_length", self.bot.config.faq_min_message_length
        )

    async def _nudge_enabled(self) -> bool:
        return (await self.bot.settings_repo.get("nudge_enabled", "1")) == "1"

    async def _nudge_cooldown_seconds(self) -> int:
        return await self.bot.settings_repo.get_int("nudge_cooldown_seconds", 600)

    # ------------------------------------------------------------------ #
    # User retrieval: /faq with autocomplete                              #
    # ------------------------------------------------------------------ #
    @app_commands.command(name="faq", description="Look up a frequently asked question.")
    @app_commands.describe(query="Search by question, keyword, or category")
    async def faq(self, interaction: discord.Interaction, query: str) -> None:
        entry = await self.bot.faq_repo.get_by_key(query)

        if entry is None:
            # The user typed free text instead of picking a suggestion: best-effort match.
            entries = await self.bot.faq_repo.all_entries()
            if entries:
                questions = {index: e.question for index, e in enumerate(entries)}
                best = process.extractOne(query, questions, scorer=fuzz.WRatio)
                if best is not None and best[1] >= 60:
                    entry = entries[best[2]]

        if entry is None:
            await interaction.response.send_message(
                "\U0001f50d I couldn't find a matching FAQ. Try different wording.",
                ephemeral=True,
            )
            return

        embed = branded_embed(title=entry.question, description=entry.answer)
        if entry.category:
            embed.set_footer(text=f"Category: {entry.category}")
        await interaction.response.send_message(embed=embed)

    @faq.autocomplete("query")
    async def _faq_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        entries = await self.bot.faq_repo.all_entries()
        if not current:
            ranked = entries[:_AUTOCOMPLETE_LIMIT]
        else:
            # Rank by question text; fall back to including the key/category.
            haystack = {
                index: f"{entry.question} {entry.key} {entry.category or ''}"
                for index, entry in enumerate(entries)
            }
            results = process.extract(
                current,
                haystack,
                scorer=fuzz.WRatio,
                limit=_AUTOCOMPLETE_LIMIT,
            )
            ranked = [entries[index] for _, _, index in results]

        return [
            app_commands.Choice(name=entry.question[:100], value=entry.key)
            for entry in ranked
        ]

    # ------------------------------------------------------------------ #
    # Staff management: interactive /faqadmin panel                       #
    # ------------------------------------------------------------------ #
    @app_commands.command(name="faqadmin", description="Open the FAQ management panel (staff only).")
    @staff_only()
    async def faq_admin(self, interaction: discord.Interaction) -> None:
        entries = await self.bot.faq_repo.all_entries()
        view = FaqAdminView(self.bot, entries, interaction.user.id)
        await interaction.response.send_message(
            embed=view.current_embed(), view=view, ephemeral=True
        )
        view.message = await interaction.original_response()

    # ------------------------------------------------------------------ #
    # Staff config: /faqconfig ...                                        #
    # ------------------------------------------------------------------ #
    config_group = app_commands.Group(
        name="faqconfig",
        description="Tune the FAQ auto-responder (staff only).",
    )

    @config_group.command(name="show", description="Show the current auto-responder settings.")
    @staff_only()
    async def faqconfig_show(self, interaction: discord.Interaction) -> None:
        optout = await self.bot.settings_repo.get_id_set("faq_optout_channels")
        optout_text = ", ".join(f"<#{cid}>" for cid in optout) if optout else "None"
        embed = branded_embed(title="FAQ Auto-Responder Settings")
        embed.add_field(
            name="Similarity threshold (semantic)",
            value=f"{await self._similarity_threshold():.2f}",
            inline=True,
        )
        embed.add_field(
            name="Fuzzy threshold",
            value=f"{await self._fuzzy_threshold():.0f}",
            inline=True,
        )
        embed.add_field(
            name="Cooldown (s)", value=str(await self._cooldown_seconds()), inline=True
        )
        embed.add_field(
            name="Min message length", value=str(await self._min_message_length()), inline=True
        )
        embed.add_field(name="Opt-out channels", value=optout_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @config_group.command(name="similarity", description="Set the semantic similarity threshold (0-1).")
    @app_commands.describe(value="Cosine similarity threshold between 0 and 1")
    @staff_only()
    async def faqconfig_similarity(
        self, interaction: discord.Interaction, value: app_commands.Range[float, 0.0, 1.0]
    ) -> None:
        await self.bot.settings_repo.set("faq_similarity_threshold", str(value))
        await interaction.response.send_message(
            f"\u2705 Similarity threshold set to {value:.2f}.", ephemeral=True
        )

    @config_group.command(name="fuzzy", description="Set the RapidFuzz fast-path threshold (0-100).")
    @app_commands.describe(value="Fuzzy score threshold between 0 and 100")
    @staff_only()
    async def faqconfig_fuzzy(
        self, interaction: discord.Interaction, value: app_commands.Range[float, 0.0, 100.0]
    ) -> None:
        await self.bot.settings_repo.set("faq_fuzzy_threshold", str(value))
        await interaction.response.send_message(
            f"\u2705 Fuzzy threshold set to {value:.0f}.", ephemeral=True
        )

    @config_group.command(name="cooldown", description="Set the per-user/channel cooldown (seconds).")
    @app_commands.describe(seconds="Cooldown in seconds")
    @staff_only()
    async def faqconfig_cooldown(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 86400]
    ) -> None:
        await self.bot.settings_repo.set("faq_cooldown_seconds", str(seconds))
        await interaction.response.send_message(
            f"\u2705 Cooldown set to {seconds}s.", ephemeral=True
        )

    @config_group.command(name="min_length", description="Set the minimum message length to consider.")
    @app_commands.describe(length="Minimum number of characters")
    @staff_only()
    async def faqconfig_min_length(
        self, interaction: discord.Interaction, length: app_commands.Range[int, 1, 2000]
    ) -> None:
        await self.bot.settings_repo.set("faq_min_message_length", str(length))
        await interaction.response.send_message(
            f"\u2705 Minimum message length set to {length}.", ephemeral=True
        )

    @config_group.command(name="optout_add", description="Exclude a channel from the auto-responder.")
    @app_commands.describe(channel="Channel to exclude")
    @staff_only()
    async def faqconfig_optout_add(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        optout = await self.bot.settings_repo.get_id_set("faq_optout_channels")
        optout.add(channel.id)
        await self.bot.settings_repo.set_id_set("faq_optout_channels", optout)
        await interaction.response.send_message(
            f"\u2705 {channel.mention} is now excluded from the auto-responder.", ephemeral=True
        )

    @config_group.command(name="optout_remove", description="Re-enable the auto-responder in a channel.")
    @app_commands.describe(channel="Channel to re-include")
    @staff_only()
    async def faqconfig_optout_remove(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        optout = await self.bot.settings_repo.get_id_set("faq_optout_channels")
        optout.discard(channel.id)
        await self.bot.settings_repo.set_id_set("faq_optout_channels", optout)
        await interaction.response.send_message(
            f"\u2705 {channel.mention} will be matched again.", ephemeral=True
        )

    # ------------------------------------------------------------------ #
    # Staff config: /nudge ...                                            #
    # ------------------------------------------------------------------ #
    nudge_group = app_commands.Group(
        name="nudge",
        description="Tune the bug/suggestion intent nudge (staff only).",
    )

    @nudge_group.command(name="show", description="Show the current nudge settings.")
    @staff_only()
    async def nudge_show(self, interaction: discord.Interaction) -> None:
        embed = branded_embed(title="Intent Nudge Settings")
        embed.add_field(
            name="Enabled", value="Yes" if await self._nudge_enabled() else "No", inline=True
        )
        embed.add_field(
            name="Cooldown (s)", value=str(await self._nudge_cooldown_seconds()), inline=True
        )
        embed.set_footer(
            text="Shares the FAQ opt-out channels and minimum message length."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @nudge_group.command(name="toggle", description="Enable or disable the intent nudge.")
    @app_commands.describe(enabled="Whether to nudge informal bug/suggestion messages")
    @staff_only()
    async def nudge_toggle(self, interaction: discord.Interaction, enabled: bool) -> None:
        await self.bot.settings_repo.set("nudge_enabled", "1" if enabled else "0")
        await interaction.response.send_message(
            f"\u2705 Intent nudge is now {'on' if enabled else 'off'}.", ephemeral=True
        )

    @nudge_group.command(name="cooldown", description="Set the per-user/channel nudge cooldown (seconds).")
    @app_commands.describe(seconds="Cooldown in seconds")
    @staff_only()
    async def nudge_cooldown(
        self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 86400]
    ) -> None:
        await self.bot.settings_repo.set("nudge_cooldown_seconds", str(seconds))
        await interaction.response.send_message(
            f"\u2705 Nudge cooldown set to {seconds}s.", ephemeral=True
        )

    # ------------------------------------------------------------------ #
    # Auto-responder                                                      #
    # ------------------------------------------------------------------ #
    def _on_cooldown(self, channel_id: int, user_id: int, cooldown: int) -> bool:
        if cooldown <= 0:
            return False
        last = self._cooldowns.get((channel_id, user_id))
        return last is not None and (time.monotonic() - last) < cooldown

    async def _handle_edit_prompt_reply(self, message: discord.Message) -> bool:
        """If this message is an admin reply to a Modify prompt, apply it.

        Returns True when the message was consumed as an answer edit.
        """

        ref = message.reference
        if ref is None or ref.message_id is None:
            return False
        prompt = await self.bot.faq_repo.get_edit_prompt(ref.message_id)
        if prompt is None or prompt.admin_id != message.author.id:
            return False

        if not message.content.strip():
            await message.reply(
                "The answer can't be empty \u2014 reply again with the answer text.",
                mention_author=False,
            )
            return True

        entry = await self.bot.faq_repo.get_by_key(prompt.faq_key)
        if entry is None:
            await self.bot.faq_repo.delete_edit_prompt(ref.message_id)
            await message.reply("That FAQ entry no longer exists.", mention_author=False)
            return True

        # Copy the reply's raw content verbatim (preserving markdown / line breaks).
        embedding = await self.bot.embedder.encode(entry.question)
        await self.bot.faq_repo.update(
            key=entry.key,
            question=entry.question,
            answer=message.content,
            category=entry.category,
            embedding=embedding,
        )
        await self.bot.faq_repo.delete_edit_prompt(ref.message_id)
        await message.reply(
            f"\u2705 Updated the answer for **{entry.key}**.", mention_author=False
        )
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # --- Safeguards -----------------------------------------------------
        if message.author.bot or message.guild is None:
            return

        # Admin reply to a "Modify answer" prompt takes priority over everything
        # else and bypasses the auto-responder safeguards (length, cooldown, ...).
        if await self._handle_edit_prompt_reply(message):
            return

        if message.type not in (discord.MessageType.default, discord.MessageType.reply):
            return

        content = message.content.strip()
        min_length = await self._min_message_length()
        if len(content) < min_length:
            return

        optout = await self.bot.settings_repo.get_id_set("faq_optout_channels")
        if message.channel.id in optout:
            return

        # --- Two-stage matching (skipped while on the FAQ cooldown) --------
        cooldown = await self._cooldown_seconds()
        result = None
        if not self._on_cooldown(message.channel.id, message.author.id, cooldown):
            result = await self.bot.matcher.find_match(
                content,
                fuzzy_threshold=await self._fuzzy_threshold(),
                similarity_threshold=await self._similarity_threshold(),
            )

        if result is not None:
            self._cooldowns[(message.channel.id, message.author.id)] = time.monotonic()
            embed = branded_embed(title=result.match.question, description=result.match.answer)
            if result.match.category:
                embed.set_footer(text=f"Category: {result.match.category}")
            try:
                await message.reply(embed=embed, mention_author=False)
            except discord.HTTPException as exc:
                log.warning("Failed to send FAQ auto-response: %s", exc)
            return

        # No FAQ match: consider nudging an informal bug report / suggestion.
        await self._maybe_nudge(message, content)

    # ------------------------------------------------------------------ #
    # Intent nudge                                                        #
    # ------------------------------------------------------------------ #
    def _report_channel_ids(self) -> set[int]:
        cfg = self.bot.config
        return {cid for cid in (cfg.bug_channel, cfg.suggestion_channel, cfg.help_channel) if cid}

    def _is_report_channel(self, channel: discord.abc.MessageableChannel) -> bool:
        ids = self._report_channel_ids()
        parent_id = getattr(channel, "parent_id", None)
        return channel.id in ids or (parent_id is not None and parent_id in ids)

    async def _maybe_nudge(self, message: discord.Message, content: str) -> None:
        if not await self._nudge_enabled():
            return
        # Pointless to nudge inside the report forums or their threads.
        if self._is_report_channel(message.channel):
            return

        cooldown = await self._nudge_cooldown_seconds()
        last = self._nudge_cooldowns.get((message.channel.id, message.author.id))
        if cooldown > 0 and last is not None and (time.monotonic() - last) < cooldown:
            return

        intent = classify(content)
        if intent is None:
            return

        self._nudge_cooldowns[(message.channel.id, message.author.id)] = time.monotonic()
        if intent is Intent.BUG:
            text = (
                "\U0001f41e It looks like you're reporting a bug \u2014 please use "
                "**/bugreport** so the team can track and fix it properly."
            )
        else:
            text = (
                "\U0001f4a1 It looks like you have a suggestion \u2014 please use "
                "**/suggest** so the team can review it properly."
            )
        try:
            await message.reply(content=text, mention_author=False)
        except discord.HTTPException as exc:
            log.warning("Failed to send intent nudge: %s", exc)


async def setup(bot: VanguardBot) -> None:
    await bot.add_cog(FAQ(bot))
