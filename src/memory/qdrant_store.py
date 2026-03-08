"""Qdrant vector store operations — upsert, search, collection management.

Wraps qdrant-client with collection setup helpers and typed search results.
Uses langchain-qdrant for LangChain-compatible retriever creation (used in evals).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, VectorParams

from src.config import get_settings
from src.llm import get_embeddings

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """A single retrieved chunk with its score and metadata."""
    content: str
    score: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_context_str(self, include_score: bool = True) -> str:
        score_str = f" [score={self.score:.3f}]" if include_score else ""
        return f"[{self.source}]{score_str}\n{self.content}"


@lru_cache
def get_qdrant_client() -> QdrantClient:
    cfg = get_settings()
    return QdrantClient(url=cfg.qdrant_url, api_key=cfg.qdrant_api_key)


def ensure_collection(collection_name: str, dim: int | None = None) -> None:
    """Create the collection if it doesn't exist."""
    cfg = get_settings()
    dim = dim or cfg.embedding_dim
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s (dim=%d)", collection_name, dim)


def upsert_chunks(
    collection_name: str,
    texts: list[str],
    vectors: list[list[float]],
    metadatas: list[dict[str, Any]],
) -> int:
    """Upsert text+vector pairs into a collection. Returns number upserted."""
    from qdrant_client.http.models import PointStruct

    client = get_qdrant_client()
    ensure_collection(collection_name, dim=len(vectors[0]))

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={"content": text, **meta},
        )
        for text, vec, meta in zip(texts, vectors, metadatas)
    ]
    client.upsert(collection_name=collection_name, points=points)
    logger.info("Upserted %d points into '%s'", len(points), collection_name)
    return len(points)


def search(
    collection_name: str,
    query_vector: list[float],
    k: int = 5,
    score_threshold: float | None = None,
    filter_conditions: dict[str, Any] | None = None,
) -> list[ChunkResult]:
    """Semantic search returning typed ChunkResult objects."""
    client = get_qdrant_client()
    qfilter = _build_filter(filter_conditions) if filter_conditions else None

    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=k,
        score_threshold=score_threshold,
        query_filter=qfilter,
    ).points

    return [
        ChunkResult(
            content=r.payload.get("content", ""),
            score=r.score,
            source=r.payload.get("source", "unknown"),
            metadata={k: v for k, v in r.payload.items() if k != "content"},
        )
        for r in results
    ]


def _build_filter(conditions: dict[str, Any]) -> Filter:
    """Build a Qdrant Filter from a {field: value} dict (AND logic)."""
    return Filter(
        must=[
            FieldCondition(key=k, match=MatchValue(value=v))
            for k, v in conditions.items()
        ]
    )


def get_langchain_retriever(collection_name: str, k: int = 5):
    """Return a LangChain-compatible retriever — used in RAGAS eval scripts."""
    ensure_collection(collection_name)
    store = QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=collection_name,
        embedding=get_embeddings(),
        content_payload_key="content",  # our chunks store text under "content" not "page_content"
    )
    return store.as_retriever(search_kwargs={"k": k})
