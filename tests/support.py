from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from typing import Any, Iterator


def make_module(name: str, **attrs: Any) -> ModuleType:
    module = ModuleType(name)
    module.__dict__.update(attrs)
    return module


@contextmanager
def patched_modules(stubs: dict[str, ModuleType]) -> Iterator[None]:
    sentinel = object()
    saved: dict[str, Any] = {name: sys.modules.get(name, sentinel) for name in stubs}
    sys.modules.update(stubs)
    try:
        yield
    finally:
        for name, original in saved.items():
            if original is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def import_module_with_stubs(module_name: str, stubs: dict[str, ModuleType]) -> ModuleType:
    sys.modules.pop(module_name, None)
    with patched_modules(stubs):
        module = importlib.import_module(module_name)
    sys.modules.pop(module_name, None)
    return module


class FakeTree:
    def __init__(self) -> None:
        self.on_error = None
        self.copied_global_to: Any = None
        self.sync_calls: list[Any] = []

    def copy_global_to(self, guild: Any) -> None:
        self.copied_global_to = guild

    async def sync(self, guild: Any) -> list[str]:
        self.sync_calls.append(guild)
        return ["synced"]


class FakeBotBase:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.command_prefix = kwargs.get("command_prefix")
        self.intents = kwargs.get("intents")
        self.help_command = kwargs.get("help_command")
        self.activity = kwargs.get("activity")
        self.status = kwargs.get("status")
        self.tree = FakeTree()
        self._loaded_extensions: list[str] = []
        self._views: list[Any] = []
        self.user = None
        self.closed = False

    async def load_extension(self, extension: str) -> None:
        self._loaded_extensions.append(extension)

    def add_view(self, view: Any) -> None:
        self._views.append(view)

    async def close(self) -> None:
        self.closed = True


class FakeIntents:
    def __init__(self) -> None:
        self.message_content = False
        self.members = False

    @classmethod
    def default(cls) -> "FakeIntents":
        return cls()


class FakeGame:
    def __init__(self, *, name: str) -> None:
        self.name = name


class FakeObject:
    def __init__(self, *, id: int) -> None:
        self.id = id


class FakeStatus:
    online = object()


class FakeDatabasePool:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.pool = object()
        self.create_calls = 0
        self.close_calls = 0

    async def create(self) -> Any:
        self.create_calls += 1
        return self.pool

    async def close(self) -> None:
        self.close_calls += 1


class FakeDatabaseSchema:
    def __init__(self, pool: Any, config: Any) -> None:
        self.pool = pool
        self.config = config
        self.init_calls = 0

    async def init(self) -> None:
        self.init_calls += 1


class FakeRepo:
    def __init__(self, pool: Any) -> None:
        self.pool = pool


class FakeEmbedder:
    def __init__(self, model: str) -> None:
        self.model = model
        self.loaded = False

    async def load(self) -> None:
        self.loaded = True


class FakeMatcher:
    def __init__(self, faq_repo: Any, embedder: Any) -> None:
        self.faq_repo = faq_repo
        self.embedder = embedder


class FakeFormsEntryView:
    def __init__(self, bot: Any) -> None:
        self.bot = bot


class FakeHoneypotWarningView:
    def __init__(self) -> None:
        self.created = True


def fake_on_app_command_error(*args: Any, **kwargs: Any) -> None:
    return None


def build_client_stubs() -> dict[str, ModuleType]:
    discord = make_module(
        "discord",
        Intents=FakeIntents,
        Game=FakeGame,
        Object=FakeObject,
        Status=FakeStatus,
    )
    discord.__path__ = []  # type: ignore[attr-defined]
    discord_ext = make_module("discord.ext")
    discord_ext.__path__ = []  # type: ignore[attr-defined]
    commands = make_module(
        "discord.ext.commands",
        Bot=FakeBotBase,
        when_mentioned=lambda *args, **kwargs: None,
    )
    discord.ext = discord_ext  # type: ignore[attr-defined]
    discord_ext.commands = commands  # type: ignore[attr-defined]

    asyncpg = make_module("asyncpg", Pool=object, Connection=object)

    cogs = make_module("cogs")
    cogs.__path__ = []  # type: ignore[attr-defined]

    bot_config = make_module("bot.config", Config=SimpleNamespace)

    db_pool = make_module("db.pool", DatabasePool=FakeDatabasePool)
    db_schema = make_module("db.schema", DatabaseSchema=FakeDatabaseSchema)

    repositories_faq = make_module("repositories.faq_repo", FaqRepository=FakeRepo)
    repositories_honeypot = make_module("repositories.honeypot_repo", HoneypotRepository=FakeRepo)
    repositories_option_sets = make_module("repositories.option_sets_repo", OptionSetsRepository=FakeRepo)
    repositories_settings = make_module("repositories.settings_repo", SettingsRepository=FakeRepo)

    services_embedder = make_module("services.embedder", Embedder=FakeEmbedder)
    services_matcher = make_module("services.matcher", Matcher=FakeMatcher)

    ui_forms_views = make_module("ui.forms_views", FormsEntryView=FakeFormsEntryView)
    ui_honeypot_view = make_module("ui.honeypot_view", HoneypotWarningView=FakeHoneypotWarningView)

    utils_errors = make_module("utils.errors", on_app_command_error=fake_on_app_command_error)

    return {
        "discord": discord,
        "discord.ext": discord_ext,
        "discord.ext.commands": commands,
        "asyncpg": asyncpg,
        "cogs": cogs,
        "bot.config": bot_config,
        "db.pool": db_pool,
        "db.schema": db_schema,
        "repositories.faq_repo": repositories_faq,
        "repositories.honeypot_repo": repositories_honeypot,
        "repositories.option_sets_repo": repositories_option_sets,
        "repositories.settings_repo": repositories_settings,
        "services.embedder": services_embedder,
        "services.matcher": services_matcher,
        "ui.forms_views": ui_forms_views,
        "ui.honeypot_view": ui_honeypot_view,
        "utils.errors": utils_errors,
    }
