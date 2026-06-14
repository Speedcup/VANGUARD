"""The VANGUARD bot: a discord.py ``commands.Bot`` wired up in ``setup_hook``."""

from __future__ import annotations

import logging
import pkgutil

import asyncpg
import discord
from discord.ext import commands

import cogs as cogs_package
from bot.config import Config
from db.pool import DatabasePool
from db.schema import DatabaseSchema
from repositories.faq_repo import FaqRepository
from repositories.honeypot_repo import HoneypotRepository
from repositories.option_sets_repo import OptionSetsRepository
from repositories.settings_repo import SettingsRepository
from services.embedder import Embedder
from services.matcher import Matcher
from ui.forms_views import FormsEntryView
from ui.honeypot_view import HoneypotWarningView
from utils.errors import on_app_command_error

log = logging.getLogger("vanguard.bot")


def _build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    # Required for the FAQ auto-responder and honeypot trigger to read content.
    intents.message_content = True
    # Required for member join/leave logging.
    intents.members = True
    return intents


class VanguardBot(commands.Bot):
    pool: asyncpg.Pool
    database_pool: DatabasePool
    database_schema: DatabaseSchema
    faq_repo: FaqRepository
    option_sets_repo: OptionSetsRepository
    settings_repo: SettingsRepository
    honeypot_repo: HoneypotRepository
    embedder: Embedder
    matcher: Matcher

    def __init__(self, config: Config) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,  # app commands only; prefix unused.
            intents=_build_intents(),
            help_command=None,
            activity=discord.Game(name="VALORANT"),
            status=discord.Status.online,
        )
        self.config = config

    async def setup_hook(self) -> None:
        # --- Persistence ----------------------------------------------------
        self.database_pool = DatabasePool(self.config.database_url)
        self.pool = await self.database_pool.create()
        self.database_schema = DatabaseSchema(self.pool, self.config)
        await self.database_schema.init()

        self.faq_repo = FaqRepository(self.pool)
        self.option_sets_repo = OptionSetsRepository(self.pool)
        self.settings_repo = SettingsRepository(self.pool)
        self.honeypot_repo = HoneypotRepository(self.pool)

        # --- Embeddings / matching -----------------------------------------
        self.embedder = Embedder(self.config.embedding_model)
        await self.embedder.load()
        self.matcher = Matcher(self.faq_repo, self.embedder)

        # --- Cogs -----------------------------------------------------------
        await self._load_cogs()

        # --- Persistent views (survive restarts) ---------------------------
        self.add_view(FormsEntryView(self))
        self.add_view(HoneypotWarningView())

        # --- Error handling + command sync ---------------------------------
        self.tree.on_error = on_app_command_error
        guild = discord.Object(id=self.config.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log.info("Synced %d application commands to guild %s.", len(synced), self.config.guild_id)

    async def _load_cogs(self) -> None:
        for module in pkgutil.iter_modules(cogs_package.__path__):
            if module.name.startswith("_"):
                continue
            extension = f"cogs.{module.name}"
            await self.load_extension(extension)
            log.info("Loaded cog: %s", extension)

    async def on_ready(self) -> None:
        if self.user is not None:
            log.info("Logged in as %s (id=%s).", self.user, self.user.id)

    async def close(self) -> None:
        await super().close()
        if hasattr(self, "database_pool"):
            await self.database_pool.close()
