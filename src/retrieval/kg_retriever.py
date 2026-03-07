"""Knowledge Graph RAG retriever — used in the chat pipeline.

Combines graph traversal with HyDE retrieval for richer, connected context:
  1. Embed the query.
  2. Find seed topic nodes in the KG by cosine similarity.
  3. Traverse graph edges (up to kg_max_hops) to discover related topics.
  4. Run HyDE retrieval for each related topic name as an expanded query.
  5. Merge, deduplicate, and re-rank all retrieved chunks by score.

This produces multi-hop context that pure dense or HyDE retrieval misses.
For example: "explain agent memory" → KG traversal also surfaces chunks
about LangGraph state, Qdrant, and retrieval — all genuinely relevant.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import get_settings
from src.llm import embed_texts
from src.memory.qdrant_store import ChunkResult
from src.memory.topic_graph import get_topic_graph
from src.retrieval.hyde_retriever import HyDERetriever

logger = logging.getLogger(__name__)


class KGRetriever:
    """Knowledge Graph + HyDE multi-hop retriever."""

    def __init__(self, collection: str | None = None) -> None:
        cfg = get_settings()
        self._collection = collection or cfg.kb_collection
        self._hyde = HyDERetriever(collection=self._collection)
        self._max_hops = cfg.kg_max_hops

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        cfg = get_settings()
        k = k or cfg.default_k

        # Step 1: embed the query
        vectors = await embed_texts([query])
        query_embedding = vectors[0]

        # Step 2: find related topic names via KG traversal
        kg = get_topic_graph()
        related_topics = kg.find_related_topics(
            query_embedding, top_k=3, max_hops=self._max_hops
        )
        logger.info("KG traversal found %d related topics: %s", len(related_topics), related_topics)

        # Step 3: HyDE retrieval on the original query + each related topic
        queries = [query] + [f"{t} in {query}" for t in related_topics[:3]]
        all_results: dict[str, ChunkResult] = {}  # content→result dedup

        for q in queries:
            results = await self._hyde.retrieve(q, k=k, filter_conditions=filter_conditions)
            for r in results:
                key = r.content[:100]  # deduplicate by content prefix
                if key not in all_results or r.score > all_results[key].score:
                    all_results[key] = r

        # Step 4: sort by score, return top-k
        merged = sorted(all_results.values(), key=lambda r: r.score, reverse=True)
        final = merged[:k]

        logger.debug(
            "KG retrieval: %d unique results from %d queries (max score=%.3f)",
            len(final),
            len(queries),
            max((r.score for r in final), default=0.0),
        )
        return final
