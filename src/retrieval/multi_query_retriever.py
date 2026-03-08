"""Multi-Query retrieval — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook:
    MultiQueryRetriever.from_llm(retriever=naive_retriever, llm=chat_model)

The LLM generates multiple reformulations of the user query. Each reformulation
retrieves documents independently. All unique retrieved documents are combined.
This improves recall by covering different phrasings of the same information need.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_classic.retrievers.multi_query import MultiQueryRetriever as _LC_MQR

from src.config import get_settings
from src.llm import get_chat_llm
from src.memory.qdrant_store import ChunkResult, get_langchain_retriever

logger = logging.getLogger(__name__)


class MultiQueryRetriever:
    """LangChain MultiQueryRetriever wrapped to return ChunkResult objects.

    Generates n alternative query phrasings via the LLM, retrieves for each,
    and returns the union of all unique retrieved documents.
    """

    def __init__(self, collection: str | None = None) -> None:
        cfg = get_settings()
        self._collection = collection or cfg.kb_collection

    def _build_retriever(self, k: int) -> _LC_MQR:
        base = get_langchain_retriever(self._collection, k=k)
        llm = get_chat_llm()
        return _LC_MQR.from_llm(retriever=base, llm=llm)

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
            logger.debug("MultiQuery retrieval: query=%r → %d unique docs", query[:60], len(results))
            return results
        except Exception:
            logger.warning("MultiQuery failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever(collection=self._collection).retrieve(query, k=k)

    def get_langchain_retriever(self, k: int = 10) -> _LC_MQR:
        """Return the raw LangChain MultiQueryRetriever for use in chains/ensembles."""
        return self._build_retriever(k)
