"""Dense vector retrieval — baseline strategy.

Embeds the raw query and searches Qdrant by cosine similarity.
Used as the Task 5 baseline in RAGAS evaluation.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings
from src.llm import embed_texts
from src.memory.qdrant_store import ChunkResult, search

logger = logging.getLogger(__name__)


class DenseRetriever:
    """Embed-and-search against a single Qdrant collection."""

    def __init__(self, collection: str | None = None) -> None:
        self._collection = collection or get_settings().kb_collection

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        cfg = get_settings()
        k = k or cfg.default_k

        vectors = await embed_texts([query])
        results = search(
            collection_name=self._collection,
            query_vector=vectors[0],
            k=k,
            filter_conditions=filter_conditions,
        )
        logger.debug(
            "Dense retrieval: query=%r → %d results (max score=%.3f)",
            query[:60],
            len(results),
            max((r.score for r in results), default=0.0),
        )
        return results
