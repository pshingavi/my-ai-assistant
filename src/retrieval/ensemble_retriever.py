"""Ensemble Retrieval (BM25 + Dense, Reciprocal Rank Fusion) — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook:
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, naive_retriever],
        weights=[0.5, 0.5]
    )

Combines BM25 sparse retrieval with dense vector retrieval using RRF (Reciprocal Rank
Fusion). Each retriever's results are ranked and their ranks are fused — documents
appearing high in both lists get a strong combined score.

The cohort notebook also includes ParentDocument, Compression, and MultiQuery in the
ensemble, but the minimal effective combination is BM25 + Dense.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_classic.retrievers.ensemble import EnsembleRetriever as _LC_EnsembleRetriever

from src.config import get_settings
from src.memory.qdrant_store import ChunkResult, get_langchain_retriever
from src.retrieval.bm25_retriever import BM25Retriever

logger = logging.getLogger(__name__)


class EnsembleRetriever:
    """BM25 + Dense ensemble using LangChain's EnsembleRetriever (RRF).

    Following Module 11: equal weighting between BM25 (sparse) and
    dense vector (semantic) retrieval.
    """

    def __init__(
        self,
        collection: str | None = None,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
    ) -> None:
        cfg = get_settings()
        self._collection = collection or cfg.kb_collection
        self._bm25_weight = bm25_weight
        self._dense_weight = dense_weight

    def _build_retriever(self, k: int) -> _LC_EnsembleRetriever:
        bm25 = BM25Retriever(collection=self._collection).get_langchain_retriever(k=k)
        dense = get_langchain_retriever(self._collection, k=k)
        return _LC_EnsembleRetriever(
            retrievers=[bm25, dense],
            weights=[self._bm25_weight, self._dense_weight],
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

        try:
            retriever = self._build_retriever(k)
            docs = await asyncio.to_thread(retriever.invoke, query)
            results = [
                ChunkResult(
                    content=doc.page_content,
                    score=1.0 / (i + 1),
                    source=doc.metadata.get("source", "unknown"),
                    metadata=doc.metadata,
                )
                for i, doc in enumerate(docs[:k])
            ]
            logger.debug("Ensemble retrieval: query=%r → %d results", query[:60], len(results))
            return results
        except Exception:
            logger.warning("Ensemble failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever(collection=self._collection).retrieve(query, k=k)

    def get_langchain_retriever(self, k: int = 10) -> _LC_EnsembleRetriever:
        """Return the raw LangChain EnsembleRetriever for use in chains."""
        return self._build_retriever(k)
