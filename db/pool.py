"""asyncpg connection-pool lifecycle.

pgvector needs its custom ``vector`` type registered on every connection, but the
type only exists once ``CREATE EXTENSION vector`` has run. To avoid a
chicken-and-egg problem we ensure the extension exists on a throwaway connection
*before* building the pool whose ``init`` hook registers the type.
"""

from __future__ import annotations

import logging

import asyncpg
from pgvector.asyncpg import register_vector

log = logging.getLogger("vanguard.db")


async def _ensure_extension(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    finally:
        await conn.close()


async def _register(conn: asyncpg.Connection) -> None:
    await register_vector(conn)


async def create_pool(dsn: str) -> asyncpg.Pool:
    """Create a pgvector-aware connection pool."""

    await _ensure_extension(dsn)
    pool = await asyncpg.create_pool(
        dsn,
        min_size=1,
        max_size=10,
        init=_register,
        command_timeout=30,
    )
    log.info("Database pool created.")
    return pool


async def close_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()
        log.info("Database pool closed.")
