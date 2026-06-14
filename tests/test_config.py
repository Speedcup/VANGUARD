from __future__ import annotations

import os
from types import ModuleType
from unittest.mock import patch

import pytest

from tests.support import import_module_with_stubs


def _import_config_module() -> ModuleType:
    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None  # type: ignore[assignment]

    return import_module_with_stubs("bot.config", {"dotenv": dotenv})


CONFIG = _import_config_module()


def test_load_uses_env_and_fallbacks() -> None:
    env = {
        "DISCORD_TOKEN": "token",
        "GUILD_ID": "123",
        "STAFF_ROLE_ID": "456",
        "DATABASE_URL": "postgresql://localhost/vanguard",
        "BUG_REPORT_CHANNEL_ID": "11",
        "REPORTS_CHANNEL_ID": "22",
        "EMBEDDING_MODEL": "test-model",
        "FAQ_SIMILARITY_THRESHOLD": "0.7",
        "FAQ_FUZZY_THRESHOLD": "91.5",
        "FAQ_COOLDOWN_SECONDS": "90",
        "FAQ_MIN_MESSAGE_LENGTH": "20",
        "HONEYPOT_SOFTBAN_SECONDS": "120",
        "DEBUG": "1",
    }

    with patch.dict(os.environ, env, clear=True):
        config = CONFIG.Config.load()

    assert config.token == "token"
    assert config.guild_id == 123
    assert config.staff_role_id == 456
    assert config.database_url == "postgresql://localhost/vanguard"
    assert config.embedding_model == "test-model"
    assert config.bug_channel == 11
    assert config.suggestion_channel == 22
    assert config.help_channel == 22
    assert config.faq_similarity_threshold == 0.7
    assert config.faq_fuzzy_threshold == 91.5
    assert config.faq_cooldown_seconds == 90
    assert config.faq_min_message_length == 20
    assert config.honeypot_softban_seconds == 120
    assert config.debug is True


def test_load_rejects_missing_required_values() -> None:
    env = {
        "DISCORD_TOKEN": "token",
        "GUILD_ID": "123",
        "DATABASE_URL": "postgresql://localhost/vanguard",
    }

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(CONFIG.ConfigError):
            CONFIG.Config.load()
