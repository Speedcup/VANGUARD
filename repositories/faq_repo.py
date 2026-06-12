"""Repository for FAQ entries and their embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import asyncpg


@dataclass(slots=True)
class FaqEntry:
    id: int
    key: str
    question: str
    answer: str
    category: str | None


@dataclass(slots=True)
class FaqMatch(FaqEntry):
    similarity: float


@dataclass(slots=True)
class FaqEditPrompt:
    prompt_message_id: int
    channel_id: int
    faq_key: str
    admin_id: int


def _entry_from_row(row: asyncpg.Record) -> FaqEntry:
    return FaqEntry(
        id=row["id"],
        key=row["key"],
        question=row["question"],
        answer=row["answer"],
        category=row["category"],
    )


class FaqRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        *,
        key: str,
        question: str,
        answer: str,
        category: str | None,
        embedding: Sequence[float],
    ) -> FaqEntry:
        row = await self._pool.fetchrow(
            """
            INSERT INTO faq_entries (key, question, answer, category, embedding)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, key, question, answer, category;
            """,
            key,
            question,
            answer,
            category,
            list(embedding),
        )
        return _entry_from_row(row)

    async def update(
        self,
        *,
        key: str,
        question: str,
        answer: str,
        category: str | None,
        embedding: Sequence[float],
    ) -> FaqEntry | None:
        row = await self._pool.fetchrow(
            """
            UPDATE faq_entries
               SET question = $2,
                   answer = $3,
                   category = $4,
                   embedding = $5,
                   updated_at = now()
             WHERE key = $1
            RETURNING id, key, question, answer, category;
            """,
            key,
            question,
            answer,
            category,
            list(embedding),
        )
        return _entry_from_row(row) if row else None

    async def delete(self, key: str) -> bool:
        result = await self._pool.execute("DELETE FROM faq_entries WHERE key = $1;", key)
        # asyncpg returns a tag like "DELETE 1".
        return result.endswith("1")

    async def get_by_key(self, key: str) -> FaqEntry | None:
        row = await self._pool.fetchrow(
            "SELECT id, key, question, answer, category FROM faq_entries WHERE key = $1;",
            key,
        )
        return _entry_from_row(row) if row else None

    async def all_entries(self) -> list[FaqEntry]:
        rows = await self._pool.fetch(
            "SELECT id, key, question, answer, category FROM faq_entries ORDER BY key;"
        )
        return [_entry_from_row(row) for row in rows]

    async def search_vector(
        self,
        embedding: Sequence[float],
        *,
        limit: int = 5,
    ) -> list[FaqMatch]:
        """Return the closest entries by cosine similarity (1 - cosine distance)."""

        rows = await self._pool.fetch(
            """
            SELECT id, key, question, answer, category,
                   1 - (embedding <=> $1::vector) AS similarity
              FROM faq_entries
             WHERE embedding IS NOT NULL
             ORDER BY embedding <=> $1::vector
             LIMIT $2;
            """,
            list(embedding),
            limit,
        )
        return [
            FaqMatch(
                id=row["id"],
                key=row["key"],
                question=row["question"],
                answer=row["answer"],
                category=row["category"],
                similarity=float(row["similarity"]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Reply-based edit prompts                                            #
    # ------------------------------------------------------------------ #
    async def create_edit_prompt(
        self,
        *,
        prompt_message_id: int,
        channel_id: int,
        faq_key: str,
        admin_id: int,
    ) -> None:
        await self._pool.execute(
            """
            INSERT INTO faq_edit_prompts (prompt_message_id, channel_id, faq_key, admin_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (prompt_message_id) DO UPDATE
               SET faq_key = EXCLUDED.faq_key,
                   admin_id = EXCLUDED.admin_id,
                   channel_id = EXCLUDED.channel_id;
            """,
            prompt_message_id,
            channel_id,
            faq_key,
            admin_id,
        )

    async def get_edit_prompt(self, prompt_message_id: int) -> FaqEditPrompt | None:
        row = await self._pool.fetchrow(
            """
            SELECT prompt_message_id, channel_id, faq_key, admin_id
              FROM faq_edit_prompts
             WHERE prompt_message_id = $1;
            """,
            prompt_message_id,
        )
        if row is None:
            return None
        return FaqEditPrompt(
            prompt_message_id=row["prompt_message_id"],
            channel_id=row["channel_id"],
            faq_key=row["faq_key"],
            admin_id=row["admin_id"],
        )

    async def delete_edit_prompt(self, prompt_message_id: int) -> None:
        await self._pool.execute(
            "DELETE FROM faq_edit_prompts WHERE prompt_message_id = $1;",
            prompt_message_id,
        )
