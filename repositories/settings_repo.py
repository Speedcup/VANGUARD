"""Repository for runtime-configurable settings stored in ``bot_settings``.

Values are cached in memory because the FAQ auto-responder reads them on every
message; the cache is refreshed whenever a value is written.
"""

from __future__ import annotations

import asyncpg


class SettingsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._cache: dict[str, str] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        rows = await self._pool.fetch("SELECT key, value FROM bot_settings;")
        self._cache = {row["key"]: row["value"] for row in rows}
        self._loaded = True

    async def get(self, key: str, default: str | None = None) -> str | None:
        await self._ensure_loaded()
        return self._cache.get(key, default)

    async def set(self, key: str, value: str) -> None:
        await self._pool.execute(
            """
            INSERT INTO bot_settings (key, value)
            VALUES ($1, $2)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            """,
            key,
            value,
        )
        self._cache[key] = value
        self._loaded = True

    async def get_float(self, key: str, default: float) -> float:
        value = await self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    async def get_int(self, key: str, default: int) -> int:
        value = await self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    async def get_id_set(self, key: str) -> set[int]:
        """Parse a CSV setting into a set of integer IDs (channels/roles)."""

        value = await self.get(key, "")
        if not value:
            return set()
        result: set[int] = set()
        for chunk in value.split(","):
            chunk = chunk.strip()
            if chunk:
                try:
                    result.add(int(chunk))
                except ValueError:
                    continue
        return result

    async def set_id_set(self, key: str, ids: set[int]) -> None:
        await self.set(key, ",".join(str(i) for i in sorted(ids)))
