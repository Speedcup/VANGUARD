"""Idempotent database initialisation: schema + first-run seeds.

Safe to run on every startup: every statement uses ``IF NOT EXISTS`` /
``ON CONFLICT DO NOTHING`` semantics, so it never clobbers existing data.
"""

from __future__ import annotations

import logging

import asyncpg

from bot.config import Config

log = logging.getLogger("vanguard.db")

# Dimensionality of all-MiniLM-L6-v2 and most MiniLM sentence-transformers models.
EMBEDDING_DIM = 384

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    "CREATE EXTENSION IF NOT EXISTS vector;",
    f"""
    CREATE TABLE IF NOT EXISTS faq_entries (
        id          BIGSERIAL PRIMARY KEY,
        key         TEXT NOT NULL UNIQUE,
        question    TEXT NOT NULL,
        answer      TEXT NOT NULL,
        category    TEXT,
        embedding   vector({EMBEDDING_DIM}),
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # Cosine-distance index for semantic search. ivfflat needs ANALYZE/data to be
    # effective but is created up-front so it is ready as entries accumulate.
    """
    CREATE INDEX IF NOT EXISTS faq_entries_embedding_idx
        ON faq_entries USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    """,
    """
    CREATE TABLE IF NOT EXISTS option_set_items (
        id            BIGSERIAL PRIMARY KEY,
        set_name      TEXT NOT NULL,
        label         TEXT NOT NULL,
        value         TEXT NOT NULL,
        description   TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        enabled       BOOLEAN NOT NULL DEFAULT TRUE,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (set_name, value)
    );
    """,
    # Backfill the description column on databases created before it existed.
    "ALTER TABLE option_set_items ADD COLUMN IF NOT EXISTS description TEXT;",
    """
    CREATE INDEX IF NOT EXISTS option_set_items_set_order_idx
        ON option_set_items (set_name, display_order);
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS honeypot_channels (
        channel_id       BIGINT PRIMARY KEY,
        guild_id         BIGINT NOT NULL,
        enabled          BOOLEAN NOT NULL DEFAULT TRUE,
        caught_count     INTEGER NOT NULL DEFAULT 0,
        embed_message_id BIGINT,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    # Links a bot "reply with the new answer" prompt message to the FAQ entry it
    # edits and the admin who triggered it. This message<->reply linkage is the
    # entire state mechanism for the reply-based Modify flow, so it survives
    # restarts without any in-memory timer.
    """
    CREATE TABLE IF NOT EXISTS faq_edit_prompts (
        prompt_message_id BIGINT PRIMARY KEY,
        channel_id        BIGINT NOT NULL,
        faq_key           TEXT NOT NULL,
        admin_id          BIGINT NOT NULL,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
)

# Generic first-run option-set seeds. Treated as a starting point and never
# overwritten (ON CONFLICT DO NOTHING), so runtime edits always win.
_SEED_OPTION_SETS: dict[str, list[str]] = {
    "suggestion_category": [
        "New Feature",
        "Improvement",
        "UI / UX",
        "Performance",
        "Other",
    ],
}

# ---------------------------------------------------------------------------
# Device option sets (iphone_model / iphone_line / ios_version)
#
# These are owned by a *versioned* seed migration rather than the plain
# first-run seeder: bumping ``CURRENT_SEED_VERSION`` re-applies the canonical
# lists below exactly once (a one-time reset), letting the model/line/version
# data evolve in code without clobbering staff edits on every restart.
# ---------------------------------------------------------------------------
CURRENT_SEED_VERSION = 2
_DEVICE_SET_NAMES: tuple[str, ...] = ("iphone_model", "iphone_line", "ios_version")

# Flat iPhone model list: every model supporting iOS 17 (A12 Bionic and later),
# plus the standalone iPhone Air. Variants (e / Pro / Plus / mini) are NOT
# encoded here — they live in the separate ``iphone_line`` set below.
_IPHONE_MODELS: tuple[str, ...] = (
    "iPhone SE (2nd generation)",
    "iPhone SE (3rd generation)",
    "iPhone XR",
    "iPhone XS",
    "iPhone XS Max",
    "iPhone 11",
    "iPhone 12",
    "iPhone 13",
    "iPhone 14",
    "iPhone 15",
    "iPhone 16",
    "iPhone 17",
    "iPhone Air",
)

# (value, label, description). ``value`` is the clean structured field stored on
# the report; ``description`` is shown beneath the option in the select menu.
# "standard" is the default line so owners of a non-variant phone aren't forced
# to pick one.
_IPHONE_LINES: tuple[tuple[str, str, str | None], ...] = (
    ("standard", "(Standard)", "The base model"),
    ("e", "e", "Apple's affordable line, introduced with the iPhone 16e"),
    ("pro", "Pro", None),
    ("pro_max", "Pro Max", None),
    ("plus", "Plus", "Larger-screen base model; discontinued after iPhone 16"),
    ("mini", "mini", "Compact small-screen model; only on iPhone 12 and 13"),
)
DEFAULT_IPHONE_LINE_VALUE = "standard"

# Released minor versions (x.y) per supported iOS major, as of mid-2026. Patch
# releases (x.y.z) are intentionally excluded; staff add new point releases at
# runtime via /options as they ship. ``major -> highest released minor``.
_IOS_MINORS: dict[int, int] = {17: 7, 18: 7, 26: 5}


def _ios_versions() -> list[str]:
    """Flat, ordered list of every seeded iOS minor version, e.g. ``17.0``."""

    versions: list[str] = []
    for major, highest in _IOS_MINORS.items():
        versions.extend(f"{major}.{minor}" for minor in range(highest + 1))
    return versions


async def _seed_option_sets(conn: asyncpg.Connection) -> None:
    for set_name, labels in _SEED_OPTION_SETS.items():
        for order, label in enumerate(labels):
            await conn.execute(
                """
                INSERT INTO option_set_items (set_name, label, value, display_order)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (set_name, value) DO NOTHING;
                """,
                set_name,
                label,
                label,
                order,
            )


async def _apply_device_seed(conn: asyncpg.Connection) -> None:
    """Reset the device sets to the canonical lists. Destructive but one-time."""

    await conn.execute(
        "DELETE FROM option_set_items WHERE set_name = ANY($1::text[]);",
        list(_DEVICE_SET_NAMES),
    )
    for order, label in enumerate(_IPHONE_MODELS):
        await conn.execute(
            """
            INSERT INTO option_set_items (set_name, label, value, display_order)
            VALUES ('iphone_model', $1, $1, $2);
            """,
            label,
            order,
        )
    for order, (value, label, description) in enumerate(_IPHONE_LINES):
        await conn.execute(
            """
            INSERT INTO option_set_items (set_name, label, value, description, display_order)
            VALUES ('iphone_line', $1, $2, $3, $4);
            """,
            label,
            value,
            description,
            order,
        )
    for order, version in enumerate(_ios_versions()):
        await conn.execute(
            """
            INSERT INTO option_set_items (set_name, label, value, display_order)
            VALUES ('ios_version', $1, $1, $2);
            """,
            version,
            order,
        )


async def _migrate_device_sets(conn: asyncpg.Connection) -> None:
    """Apply the device seed once per ``CURRENT_SEED_VERSION`` bump."""

    stored = await conn.fetchval("SELECT value FROM bot_settings WHERE key = 'seed_version';")
    version = int(stored) if stored and str(stored).isdigit() else 0
    if version >= CURRENT_SEED_VERSION:
        return

    await _apply_device_seed(conn)
    await conn.execute(
        """
        INSERT INTO bot_settings (key, value) VALUES ('seed_version', $1)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
        """,
        str(CURRENT_SEED_VERSION),
    )
    log.info("Applied device seed migration (v%d).", CURRENT_SEED_VERSION)


async def _seed_settings(conn: asyncpg.Connection, config: Config) -> None:
    defaults = {
        "faq_similarity_threshold": str(config.faq_similarity_threshold),
        "faq_fuzzy_threshold": str(config.faq_fuzzy_threshold),
        "faq_cooldown_seconds": str(config.faq_cooldown_seconds),
        "faq_min_message_length": str(config.faq_min_message_length),
        "faq_optout_channels": "",  # CSV of channel IDs the auto-responder ignores.
        "nudge_enabled": "1",  # Whether to nudge informal bug/suggestion messages.
        "nudge_cooldown_seconds": "600",  # Per-user/channel cooldown between nudges.
        "honeypot_softban_seconds": str(config.honeypot_softban_seconds),
        "honeypot_exempt_roles": "",  # CSV of role IDs exempt from the trap.
    }
    for key, value in defaults.items():
        await conn.execute(
            """
            INSERT INTO bot_settings (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO NOTHING;
            """,
            key,
            value,
        )


async def init_db(pool: asyncpg.Pool, config: Config) -> None:
    """Create tables/extensions and seed first-run data. Idempotent."""

    async with pool.acquire() as conn:
        async with conn.transaction():
            for statement in _SCHEMA_STATEMENTS:
                await conn.execute(statement)
            await _seed_option_sets(conn)
            await _seed_settings(conn, config)
            await _migrate_device_sets(conn)
    log.info("Database schema initialised and seeds applied.")
