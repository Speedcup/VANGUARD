"""Repository for database-backed, runtime-editable option sets.

An "option set" is a named, ordered collection of selectable values (e.g.
``iphone_model``, ``ios_version``, ``suggestion_category``). Select menus across
the bot read live from here, so adding or retiring an option requires no code
change or redeploy.
"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg


@dataclass(slots=True)
class OptionItem:
    id: int
    set_name: str
    label: str
    value: str
    description: str | None
    display_order: int
    enabled: bool


_SELECT_COLUMNS = "id, set_name, label, value, description, display_order, enabled"


def _item_from_row(row: asyncpg.Record) -> OptionItem:
    return OptionItem(
        id=row["id"],
        set_name=row["set_name"],
        label=row["label"],
        value=row["value"],
        description=row["description"],
        display_order=row["display_order"],
        enabled=row["enabled"],
    )


class OptionSetsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def set_names(self) -> list[str]:
        rows = await self._pool.fetch(
            "SELECT DISTINCT set_name FROM option_set_items ORDER BY set_name;"
        )
        return [row["set_name"] for row in rows]

    async def items(self, set_name: str, *, enabled_only: bool = False) -> list[OptionItem]:
        query = f"""
            SELECT {_SELECT_COLUMNS}
              FROM option_set_items
             WHERE set_name = $1
        """
        if enabled_only:
            query += " AND enabled = TRUE"
        query += " ORDER BY display_order, label;"
        rows = await self._pool.fetch(query, set_name)
        return [_item_from_row(row) for row in rows]

    async def get(self, set_name: str, value: str) -> OptionItem | None:
        row = await self._pool.fetchrow(
            f"""
            SELECT {_SELECT_COLUMNS}
              FROM option_set_items
             WHERE set_name = $1 AND value = $2;
            """,
            set_name,
            value,
        )
        return _item_from_row(row) if row else None

    async def add(
        self,
        *,
        set_name: str,
        label: str,
        value: str,
        description: str | None = None,
        display_order: int | None = None,
    ) -> OptionItem | None:
        """Add an option. Returns ``None`` if the value already exists in the set."""

        if display_order is None:
            next_order = await self._pool.fetchval(
                "SELECT COALESCE(MAX(display_order) + 1, 0) FROM option_set_items WHERE set_name = $1;",
                set_name,
            )
            display_order = int(next_order)

        row = await self._pool.fetchrow(
            f"""
            INSERT INTO option_set_items (set_name, label, value, description, display_order)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (set_name, value) DO NOTHING
            RETURNING {_SELECT_COLUMNS};
            """,
            set_name,
            label,
            value,
            description,
            display_order,
        )
        return _item_from_row(row) if row else None

    async def edit(
        self,
        *,
        set_name: str,
        value: str,
        label: str | None = None,
        description: str | None = None,
        display_order: int | None = None,
    ) -> OptionItem | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE option_set_items
               SET label = COALESCE($3, label),
                   description = COALESCE($4, description),
                   display_order = COALESCE($5, display_order)
             WHERE set_name = $1 AND value = $2
            RETURNING {_SELECT_COLUMNS};
            """,
            set_name,
            value,
            label,
            description,
            display_order,
        )
        return _item_from_row(row) if row else None

    async def set_enabled(self, set_name: str, value: str, enabled: bool) -> OptionItem | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE option_set_items
               SET enabled = $3
             WHERE set_name = $1 AND value = $2
            RETURNING {_SELECT_COLUMNS};
            """,
            set_name,
            value,
            enabled,
        )
        return _item_from_row(row) if row else None

    async def remove(self, set_name: str, value: str) -> bool:
        result = await self._pool.execute(
            "DELETE FROM option_set_items WHERE set_name = $1 AND value = $2;",
            set_name,
            value,
        )
        return result.endswith("1")
