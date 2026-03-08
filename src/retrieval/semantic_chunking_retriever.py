"""Semantic Chunking + Retrieval — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook:
    semantic_chunker = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
    semantic_documents = semantic_chunker.split_documents(raw_docs)
    semantic_vectorstore = QdrantVectorStore.from_documents(...)
    semantic_retriever = semantic_vectorstore.as_retriever(search_kwargs={"k": 10})

Semantic chunking splits text at natural topic boundaries (based on sentence embedding
distances) rather than fixed character counts. Requires langchain-experimental.

Unlike other retrievers, this is primarily a CHUNKING STRATEGY rather than a retrieval
strategy — it uses naive dense retrieval but over semantically coherent chunks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.memory.qdrant_store import ChunkResult

logger = logging.getLogger(__name__)

# Module-level cache
_cached_retriever = None

_SOURCE_BASE = Path(__file__).parent.parent.parent.parent / "Learn-AI-Engineering"

_SOURCE_FILES = [
    _SOURCE_BASE / "03_The_Agent_Loop" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "04_Agentic_RAG_From_Scratch" / "fun_guide.md",
    _SOURCE_BASE / "02_Dense_Vector_Retrieval" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "11_Advanced_Retrieval" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "11_Advanced_Retrieval" / "data" / "MentalHealthGuide.txt",
]


def _load_raw_docs():
    from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader

    docs = []
    seen_names = set()
    for path in _SOURCE_FILES:
        if not path.exists():
            continue
        name = path.name
        if name in seen_names:
            continue
        seen_names.add(name)
        try:
            if path.suffix == ".md":
                loader = UnstructuredMarkdownLoader(str(path))
            else:
                loader = TextLoader(str(path), encoding="utf-8")
            docs.extend(loader.load())
            logger.info("SemanticChunking: loaded %s", name)
        except Exception:
            logger.warning("SemanticChunking: could not load %s", path, exc_info=True)
    return docs


def _build_semantic_retriever(k: int):
    """Build semantic chunker + vector store (runs once per process)."""
    from langchain_experimental.text_splitter import SemanticChunker
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client import models as qdrant_models

    from src.llm import get_embeddings

    cfg = get_settings()
    embeddings = get_embeddings()

    raw_docs = _load_raw_docs()
    if not raw_docs:
        logger.warning("SemanticChunking: no source documents found")
        return None

    # Semantic chunking with percentile threshold (Module 11 pattern)
    semantic_chunker = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
    )
    semantic_docs = semantic_chunker.split_documents(raw_docs)
    logger.info(
        "SemanticChunking: %d raw docs → %d semantic chunks",
        len(raw_docs), len(semantic_docs),
    )

    # In-memory Qdrant for semantic-chunked collection
    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name="course_kb_semantic",
        vectors_config=qdrant_models.VectorParams(
            size=cfg.embedding_dim, distance=qdrant_models.Distance.COSINE
        ),
    )
    vectorstore = QdrantVectorStore.from_documents(
        semantic_docs,
        embeddings,
        client=client,
        collection_name="course_kb_semantic",
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


def _get_retriever(k: int):
    global _cached_retriever
    if _cached_retriever is None:
        _cached_retriever = _build_semantic_retriever(k)
    return _cached_retriever


class SemanticChunkingRetriever:
    """Naive dense retrieval over semantically-chunked documents (Module 11).

    Uses SemanticChunker (percentile threshold) to split documents at natural
    topic boundaries, then indexes and retrieves with dense cosine search.
    """

    def __init__(self) -> None:
        pass  # built lazily

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
            retriever = await asyncio.to_thread(_get_retriever, k)
            if retriever is None:
                raise RuntimeError("Could not build semantic retriever (no source docs)")
            docs = await asyncio.to_thread(retriever.invoke, query)
            results = [
                ChunkResult(
                    content=doc.page_content,
                    score=1.0 / (i + 1),
                    source=doc.metadata.get("source", "semantic"),
                    metadata=doc.metadata,
                )
                for i, doc in enumerate(docs[:k])
            ]
            logger.debug("SemanticChunking retrieval: query=%r → %d results", query[:60], len(results))
            return results
        except Exception:
            logger.warning("SemanticChunking failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever().retrieve(query, k=k)
