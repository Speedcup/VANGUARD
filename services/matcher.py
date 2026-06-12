"""Two-stage FAQ matching: cheap RapidFuzz fast-path, then pgvector semantics.

Stage 1 (fuzzy) catches near-exact phrasing without touching the embedding model
or the DB vector index. Only when that fails do we pay for an embedding + a
vector search. Both stages use configurable thresholds tuned to err on the side
of staying silent rather than answering wrongly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz, process

from repositories.faq_repo import FaqMatch, FaqRepository
from services.embedder import Embedder

log = logging.getLogger("vanguard.matcher")


class MatchMethod(str, Enum):
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"


@dataclass(slots=True)
class MatchResult:
    match: FaqMatch
    method: MatchMethod
    score: float


class Matcher:
    def __init__(self, faq_repo: FaqRepository, embedder: Embedder) -> None:
        self._faq_repo = faq_repo
        self._embedder = embedder

    async def find_match(
        self,
        text: str,
        *,
        fuzzy_threshold: float,
        similarity_threshold: float,
    ) -> MatchResult | None:
        entries = await self._faq_repo.all_entries()
        if not entries:
            return None

        # --- Stage 1: RapidFuzz fast-path over the questions --------------------
        questions = {index: entry.question for index, entry in enumerate(entries)}
        fuzzy = process.extractOne(text, questions, scorer=fuzz.token_set_ratio)
        if fuzzy is not None:
            _, fuzzy_score, index = fuzzy
            if fuzzy_score >= fuzzy_threshold:
                entry = entries[index]
                return MatchResult(
                    match=FaqMatch(
                        id=entry.id,
                        key=entry.key,
                        question=entry.question,
                        answer=entry.answer,
                        category=entry.category,
                        similarity=fuzzy_score / 100.0,
                    ),
                    method=MatchMethod.FUZZY,
                    score=fuzzy_score,
                )

        # --- Stage 2: semantic search via pgvector cosine similarity ------------
        embedding = await self._embedder.encode(text)
        candidates = await self._faq_repo.search_vector(embedding, limit=1)
        if candidates:
            best = candidates[0]
            if best.similarity >= similarity_threshold:
                return MatchResult(
                    match=best,
                    method=MatchMethod.SEMANTIC,
                    score=best.similarity,
                )

        return None
