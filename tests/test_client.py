from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest

from tests.support import build_client_stubs, import_module_with_stubs


CLIENT = import_module_with_stubs("bot.client", build_client_stubs())


def test_build_intents_enables_required_flags() -> None:
    intents = CLIENT._build_intents()

    assert intents.message_content is True
    assert intents.members is True


@pytest.mark.asyncio
async def test_setup_hook_wires_database_and_repos() -> None:
    config = SimpleNamespace(
        database_url="postgresql://localhost/vanguard",
        embedding_model="test-model",
        guild_id=321,
    )
    bot = CLIENT.VanguardBot(config)
    bot._load_cogs = AsyncMock()

    await bot.setup_hook()

    assert bot.database_pool.dsn == "postgresql://localhost/vanguard"
    assert bot.database_pool.create_calls == 1
    assert bot.pool is bot.database_pool.pool
    assert bot.database_schema.pool is bot.pool
    assert bot.database_schema.config is config
    assert bot.faq_repo.pool is bot.pool
    assert bot.option_sets_repo.pool is bot.pool
    assert bot.settings_repo.pool is bot.pool
    assert bot.honeypot_repo.pool is bot.pool
    assert bot.embedder.model == "test-model"
    assert bot.embedder.loaded is True
    assert bot.matcher.faq_repo is bot.faq_repo
    assert bot.matcher.embedder is bot.embedder
    bot._load_cogs.assert_awaited_once()
    assert len(bot._views) == 2
    assert bot._views[0].bot is bot
    assert bot._views[1].created is True
    assert bot.tree.on_error is CLIENT.on_app_command_error
    assert bot.tree.copied_global_to.id == 321
    assert bot.tree.sync_calls[0].id == 321


@pytest.mark.asyncio
async def test_load_cogs_skips_private_extensions(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = CLIENT.VanguardBot(SimpleNamespace(database_url="db", embedding_model="model", guild_id=1))
    bot.load_extension = AsyncMock()

    fake_modules = [
        SimpleNamespace(name="_private"),
        SimpleNamespace(name="faq"),
        SimpleNamespace(name="members"),
    ]
    monkeypatch.setattr(CLIENT.pkgutil, "iter_modules", lambda path: iter(fake_modules))

    await bot._load_cogs()

    bot.load_extension.assert_has_awaits([call("cogs.faq"), call("cogs.members")])


@pytest.mark.asyncio
async def test_close_closes_database_pool() -> None:
    bot = CLIENT.VanguardBot(SimpleNamespace(database_url="db", embedding_model="model", guild_id=1))
    bot.database_pool = SimpleNamespace(close=AsyncMock())

    await bot.close()

    assert bot.closed is True
    bot.database_pool.close.assert_awaited_once()
