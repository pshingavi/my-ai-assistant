"""HyDE (Hypothetical Document Embeddings) retriever — Task 6 advanced strategy.

Instead of embedding the raw query, we:
  1. Ask the LLM to write a hypothetical answer to the query.
  2. Embed that hypothetical document (technical vocab → better KB match).
  3. Search Qdrant with the hypothetical embedding.
  4. Fall back to dense retrieval on any failure.

Why HyDE for this use case:
  LinkedIn post creation queries are conversational ("what's trending in RAG?")
  while the knowledge base contains technical course material.
  HyDE bridges this semantic gap significantly — see RAGAS results in README.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.llm import embed_texts, get_async_openai
from src.memory.qdrant_store import ChunkResult, search
from src.retrieval.dense_retriever import DenseRetriever

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

_HYDE_PROMPT = (
    "Write a short, detailed technical explanation that would answer the following "
    "question. Write as if you are explaining it to an AI engineer. "
    "Do not mention that you are writing a hypothetical document.\n\n"
    "Question: {query}"
)


class HyDERetriever:
    """HyDE retrieval with automatic dense fallback."""

    def __init__(self, collection: str | None = None) -> None:
        cfg = get_settings()
        self._collection = collection or cfg.kb_collection
        self._dense = DenseRetriever(collection=self._collection)

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        cfg = get_settings()
        k = k or cfg.default_k

        try:
            hypothetical = await self._generate_hypothetical(query)
            vectors = await embed_texts([hypothetical])
            results = search(
                collection_name=self._collection,
                query_vector=vectors[0],
                k=k,
                filter_conditions=filter_conditions,
            )
            logger.debug(
                "HyDE retrieval: query=%r → %d results (max score=%.3f)",
                query[:60],
                len(results),
                max((r.score for r in results), default=0.0),
            )
            return results
        except Exception:
            logger.warning("HyDE failed — falling back to dense retrieval", exc_info=True)
            return await self._dense.retrieve(query, k=k, filter_conditions=filter_conditions)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def _generate_hypothetical(self, query: str) -> str:
        cfg = get_settings()
        client = get_async_openai()
        response = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=[{"role": "user", "content": _HYDE_PROMPT.format(query=query)}],
            max_tokens=cfg.hyde_max_tokens,
            temperature=0.5,
        )
        text = response.choices[0].message.content or ""
        return _THINK_RE.sub("", text).strip()


def get_retriever(use_hyde: bool | None = None) -> HyDERetriever | DenseRetriever:
    """Factory: returns HyDE or Dense based on config or explicit override."""
    cfg = get_settings()
    if (use_hyde if use_hyde is not None else cfg.hyde_enabled):
        return HyDERetriever()
    return DenseRetriever()
