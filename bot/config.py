"""Environment-driven configuration for the VANGUARD bot.

All runtime configuration is sourced from environment variables (optionally via a
local ``.env`` file). Values that staff can change at runtime (matching
thresholds, cooldowns, honeypot durations) are only *seeded* from here on first
run and thereafter live in the ``bot_settings`` table.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing or malformed."""


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Required environment variable {name!r} is not set.")
    return value


def _require_int(name: str) -> int:
    raw = _require(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name!r} must be an integer.") from exc


def _optional_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name!r} must be an integer.") from exc


def _float_default(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name!r} must be a float.") from exc


def _int_default(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name!r} must be an integer.") from exc


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable, fully validated runtime configuration."""

    token: str
    guild_id: int
    staff_role_id: int

    database_url: str
    embedding_model: str

    bug_report_channel_id: int | None
    suggestion_channel_id: int | None
    help_channel_id: int | None
    reports_channel_id: int | None
    member_log_channel_id: int | None
    mod_log_channel_id: int | None

    # Seed values for bot_settings (only used the first time the DB is initialised).
    faq_similarity_threshold: float
    faq_fuzzy_threshold: float
    faq_cooldown_seconds: int
    faq_min_message_length: int
    honeypot_softban_seconds: int

    debug: bool

    @property
    def bug_channel(self) -> int | None:
        return self.bug_report_channel_id or self.reports_channel_id

    @property
    def suggestion_channel(self) -> int | None:
        return self.suggestion_channel_id or self.reports_channel_id

    @property
    def help_channel(self) -> int | None:
        return self.help_channel_id or self.reports_channel_id

    @classmethod
    def load(cls) -> "Config":
        return cls(
            token=_require("DISCORD_TOKEN"),
            guild_id=_require_int("GUILD_ID"),
            staff_role_id=_require_int("STAFF_ROLE_ID"),
            database_url=_require("DATABASE_URL"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            bug_report_channel_id=_optional_int("BUG_REPORT_CHANNEL_ID"),
            suggestion_channel_id=_optional_int("SUGGESTION_CHANNEL_ID"),
            help_channel_id=_optional_int("HELP_CHANNEL_ID"),
            reports_channel_id=_optional_int("REPORTS_CHANNEL_ID"),
            member_log_channel_id=_optional_int("MEMBER_LOG_CHANNEL_ID"),
            mod_log_channel_id=_optional_int("MOD_LOG_CHANNEL_ID"),
            faq_similarity_threshold=_float_default("FAQ_SIMILARITY_THRESHOLD", 0.62),
            faq_fuzzy_threshold=_float_default("FAQ_FUZZY_THRESHOLD", 90.0),
            faq_cooldown_seconds=_int_default("FAQ_COOLDOWN_SECONDS", 60),
            faq_min_message_length=_int_default("FAQ_MIN_MESSAGE_LENGTH", 15),
            honeypot_softban_seconds=_int_default("HONEYPOT_SOFTBAN_SECONDS", 60),
            debug=os.environ.get("DEBUG", "0") not in ("", "0", "false", "False"),
        )
