"""Repository for honeypot trap channels and their caught-account counters."""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class HoneypotChannel:
    channel_id: int
    guild_id: int
    enabled: bool
    caught_count: int
    embed_message_id: int | None


def _from_row(row: asyncpg.Record) -> HoneypotChannel:
    return HoneypotChannel(
        channel_id=row["channel_id"],
        guild_id=row["guild_id"],
        enabled=row["enabled"],
        caught_count=row["caught_count"],
        embed_message_id=row["embed_message_id"],
    )


class HoneypotRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(
        self,
        *,
        channel_id: int,
        guild_id: int,
        embed_message_id: int | None,
    ) -> HoneypotChannel:
        row = await self._pool.fetchrow(
            """
            INSERT INTO honeypot_channels (channel_id, guild_id, enabled, embed_message_id)
            VALUES ($1, $2, TRUE, $3)
            ON CONFLICT (channel_id) DO UPDATE
               SET enabled = TRUE,
                   embed_message_id = EXCLUDED.embed_message_id
            RETURNING channel_id, guild_id, enabled, caught_count, embed_message_id;
            """,
            channel_id,
            guild_id,
            embed_message_id,
        )
        return _from_row(row)

    async def disable(self, channel_id: int) -> bool:
        result = await self._pool.execute(
            "UPDATE honeypot_channels SET enabled = FALSE WHERE channel_id = $1;",
            channel_id,
        )
        return result.endswith("1")

    async def get(self, channel_id: int) -> HoneypotChannel | None:
        row = await self._pool.fetchrow(
            """
            SELECT channel_id, guild_id, enabled, caught_count, embed_message_id
              FROM honeypot_channels
             WHERE channel_id = $1;
            """,
            channel_id,
        )
        return _from_row(row) if row else None

    async def enabled_channel_ids(self) -> set[int]:
        rows = await self._pool.fetch(
            "SELECT channel_id FROM honeypot_channels WHERE enabled = TRUE;"
        )
        return {row["channel_id"] for row in rows}

    async def increment_caught(self, channel_id: int) -> int:
        """Increment and return the new caught count."""

        return int(
            await self._pool.fetchval(
                """
                UPDATE honeypot_channels
                   SET caught_count = caught_count + 1
                 WHERE channel_id = $1
                RETURNING caught_count;
                """,
                channel_id,
            )
        )
