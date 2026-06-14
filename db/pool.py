"""asyncpg connection-pool lifecycle."""

from __future__ import annotations

import logging

import asyncpg
from pgvector.asyncpg import register_vector

log = logging.getLogger("vanguard.db")


class DatabasePool:
    """Manage the pgvector-aware asyncpg pool lifecycle."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool | None:
        return self._pool

    async def _ensure_extension(self) -> None:
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        finally:
            await conn.close()

    async def _register(self, conn: asyncpg.Connection) -> None:
        await register_vector(conn)

    async def create(self) -> asyncpg.Pool:
        """Create and cache a pgvector-aware connection pool."""

        await self._ensure_extension()
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=1,
            max_size=10,
            init=self._register,
            command_timeout=30,
        )
        log.info("Database pool created.")
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            log.info("Database pool closed.")
