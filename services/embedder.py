"""Local sentence-transformers embedding service.

The model is loaded once at startup and all encode calls are dispatched to a
worker thread so the (CPU-bound, blocking) inference never stalls the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = logging.getLogger("vanguard.embedder")


class Embedder:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: "SentenceTransformer | None" = None

    def _load_sync(self) -> None:
        from sentence_transformers import SentenceTransformer

        log.info("Loading embedding model %r ...", self._model_name)
        self._model = SentenceTransformer(self._model_name)
        log.info("Embedding model loaded.")

    async def load(self) -> None:
        """Load (download if necessary) the model off the event loop."""

        await asyncio.to_thread(self._load_sync)

    @property
    def dimension(self) -> int:
        if self._model is None:
            raise RuntimeError("Embedder.load() must be awaited before use.")
        return int(self._model.get_sentence_embedding_dimension())

    def _encode_sync(self, text: str) -> list[float]:
        assert self._model is not None  # guarded by encode()
        # Normalised embeddings make cosine similarity well-behaved in [-1, 1].
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    async def encode(self, text: str) -> list[float]:
        if self._model is None:
            raise RuntimeError("Embedder.load() must be awaited before use.")
        return await asyncio.to_thread(self._encode_sync, text)
