"""Contextual Compression + Cohere Rerank — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook:
    compressor = CohereRerank(model="rerank-v3.5")
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=naive_retriever
    )

Requires COHERE_API_KEY in .env (free tier at dashboard.cohere.com/api-keys).
Falls back to naive dense retrieval if key is absent.

Rate-limit handling: Cohere free-tier allows ~5 req/min.
tenacity retries with exponential backoff handle TooManyRequests (429) errors.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import get_settings
from src.memory.qdrant_store import ChunkResult, get_langchain_retriever

logger = logging.getLogger(__name__)

# Cohere free tier: ~5 req/min. Keep a conservative inter-call delay.
_COHERE_DELAY_S = 2.0  # seconds between Cohere calls


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__
    msg = str(exc).lower()
    return "429" in msg or "too many" in msg or "rate" in msg or name in ("TooManyRequestsError",)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    reraise=True,
)
def _invoke_with_retry(retriever, query: str):
    """Invoke the compression retriever with tenacity retry on rate-limit errors."""
    result = retriever.invoke(query)
    time.sleep(_COHERE_DELAY_S)  # throttle to stay under Cohere free-tier limits
    return result


class RerankRetriever:
    """Contextual Compression with Cohere Rerank v3.5 (Module 11 pattern).

    Two-step process:
      1. Base dense retriever fetches k*3 candidate chunks from Qdrant.
      2. Cohere rerank-v3.5 reorders and filters to top-k most relevant.

    Requires COHERE_API_KEY. Gracefully falls back to dense retrieval if absent.
    Handles Cohere free-tier rate limits with tenacity exponential-backoff retries.
    """

    def __init__(self, collection: str | None = None) -> None:
        cfg = get_settings()
        self._collection = collection or cfg.kb_collection
        self._has_cohere = bool(
            cfg.cohere_api_key or os.environ.get("COHERE_API_KEY")
        )
        if not self._has_cohere:
            logger.warning(
                "COHERE_API_KEY not set — RerankRetriever falls back to dense. "
                "Add COHERE_API_KEY to .env (free tier: dashboard.cohere.com/api-keys)."
            )

    def _build_retriever(self, k: int):
        from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
        from langchain_cohere import CohereRerank

        base_retriever = get_langchain_retriever(self._collection, k=k * 3)
        # Cohere rerank-v3.5 as used in Module 11 notebook
        compressor = CohereRerank(model="rerank-v3.5", top_n=k)
        return ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever,
        )

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        import asyncio

        cfg = get_settings()
        k = k or cfg.default_k

        if not self._has_cohere:
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever(collection=self._collection).retrieve(query, k=k)

        try:
            retriever = self._build_retriever(k)
            docs = await asyncio.to_thread(_invoke_with_retry, retriever, query)
            results = [
                ChunkResult(
                    content=doc.page_content,
                    score=doc.metadata.get("relevance_score", 1.0 / (i + 1)),
                    source=doc.metadata.get("source", "unknown"),
                    metadata=doc.metadata,
                )
                for i, doc in enumerate(docs[:k])
            ]
            logger.debug("Rerank retrieval: query=%r → %d results", query[:60], len(results))
            return results
        except Exception:
            logger.warning("Rerank failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever(collection=self._collection).retrieve(query, k=k)

    def get_langchain_retriever(self, k: int = 10):
        """Return raw LangChain ContextualCompressionRetriever for use in chains."""
        if not self._has_cohere:
            return get_langchain_retriever(self._collection, k=k)
        return self._build_retriever(k)
