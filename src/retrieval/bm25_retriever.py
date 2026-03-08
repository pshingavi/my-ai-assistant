"""BM25 (Best-Matching 25) sparse retrieval — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook: uses LangChain's BM25Retriever built from
documents scrolled out of the existing Qdrant collection.

BM25 is bag-of-words based: it finds documents that share keywords with the query.
Complements dense embeddings, which capture semantic similarity.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_community.retrievers import BM25Retriever as _LC_BM25Retriever
from langchain_core.documents import Document

from src.config import get_settings
from src.memory.qdrant_store import ChunkResult, get_qdrant_client

logger = logging.getLogger(__name__)

# Module-level cache: collection_name → BM25Retriever instance
_bm25_cache: dict[str, _LC_BM25Retriever] = {}


def _build_bm25_retriever(collection_name: str, k: int) -> _LC_BM25Retriever:
    """Scroll all documents from Qdrant and build an in-memory BM25 index."""
    client = get_qdrant_client()
    documents: list[Document] = []
    offset = None

    while True:
        results, offset = client.scroll(
            collection_name=collection_name,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in results:
            content = point.payload.get("content", "")
            source = point.payload.get("source", "unknown")
            if content:
                documents.append(Document(page_content=content, metadata={"source": source}))
        if offset is None:
            break

    logger.info("BM25: built index from %d documents in '%s'", len(documents), collection_name)
    retriever = _LC_BM25Retriever.from_documents(documents)
    retriever.k = k
    return retriever


def _get_bm25(collection_name: str, k: int) -> _LC_BM25Retriever:
    """Return cached BM25 retriever, rebuilding if k changed."""
    key = f"{collection_name}:{k}"
    if key not in _bm25_cache:
        _bm25_cache[key] = _build_bm25_retriever(collection_name, k)
    return _bm25_cache[key]


class BM25Retriever:
    """Sparse keyword retriever using BM25Okapi via LangChain community package.

    Follows the Module 11 pattern: BM25Retriever.from_documents(docs).
    Index is built once per collection and cached in memory.
    """

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

        try:
            retriever = await asyncio.to_thread(_get_bm25, self._collection, k)
            docs = await asyncio.to_thread(retriever.invoke, query)
            results = [
                ChunkResult(
                    content=doc.page_content,
                    score=1.0 / (i + 1),  # rank-based pseudo-score
                    source=doc.metadata.get("source", "unknown"),
                    metadata=doc.metadata,
                )
                for i, doc in enumerate(docs)
            ]
            logger.debug("BM25 retrieval: query=%r → %d results", query[:60], len(results))
            return results
        except Exception:
            logger.warning("BM25 failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever(collection=self._collection).retrieve(query, k=k)

    def get_langchain_retriever(self, k: int = 10) -> _LC_BM25Retriever:
        """Return the raw LangChain BM25Retriever for use in chains/ensembles."""
        return _get_bm25(self._collection, k)
