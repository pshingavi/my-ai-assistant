"""Parent-Document Retrieval — Module 11 cohort implementation.

Based on AIE9 Session 11 notebook:
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter  = RecursiveCharacterTextSplitter(chunk_size=400,  chunk_overlap=50)
    store = InMemoryStore()
    retriever = ParentDocumentRetriever(
        vectorstore=parent_document_vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )

"Small-to-big" strategy:
  - Index small child chunks (400 chars) for precise semantic matching
  - Return their large parent chunks (2000 chars) for richer context

Requires source documents to be ingested via add_documents() before retrieval.
This class manages its own Qdrant collection ("course_kb_parent_doc") and builds
the parent-child index on first use from the same source files used by the main KB.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_classic.retrievers.parent_document_retriever import ParentDocumentRetriever as _LC_PDR
from langchain_core.stores import InMemoryBaseStore as InMemoryStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

from src.config import get_settings
from src.llm import get_embeddings
from src.memory.qdrant_store import ChunkResult

logger = logging.getLogger(__name__)

PARENT_COLLECTION = "course_kb_parent_doc"

# Module-level cache so we only build once per process
_cached_retriever: _LC_PDR | None = None
_cached_store: InMemoryStore | None = None


# Source documents used in the testset (same as synthetic_data_gen.py)
_SOURCE_BASE = Path(__file__).parent.parent.parent.parent / "Learn-AI-Engineering"

_SOURCE_FILES = [
    _SOURCE_BASE / "03_The_Agent_Loop" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "04_Agentic_RAG_From_Scratch" / "fun_guide.md",
    _SOURCE_BASE / "02_Dense_Vector_Retrieval" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "11_Advanced_Retrieval" / "data" / "HealthWellnessGuide.txt",
    _SOURCE_BASE / "11_Advanced_Retrieval" / "data" / "MentalHealthGuide.txt",
]


def _load_raw_docs():
    """Load raw (unsplit) source documents."""
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
            loaded = loader.load()
            docs.extend(loaded)
            logger.info("ParentDoc: loaded %s (%d docs)", name, len(loaded))
        except Exception:
            logger.warning("ParentDoc: could not load %s", path, exc_info=True)

    if not docs:
        logger.warning("ParentDoc: no source documents found, will return empty results")
    return docs


def _build_parent_doc_retriever() -> _LC_PDR:
    """Build and populate the ParentDocumentRetriever (runs once per process)."""
    from langchain_qdrant import QdrantVectorStore

    cfg = get_settings()
    embeddings = get_embeddings()

    # Create an in-memory Qdrant client for parent-doc (separate from main KB)
    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name=PARENT_COLLECTION,
        vectors_config=qdrant_models.VectorParams(
            size=cfg.embedding_dim, distance=qdrant_models.Distance.COSINE
        ),
    )
    vectorstore = QdrantVectorStore(
        collection_name=PARENT_COLLECTION,
        embedding=embeddings,
        client=client,
    )

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
    store = InMemoryStore()

    retriever = _LC_PDR(
        vectorstore=vectorstore,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
    )

    raw_docs = _load_raw_docs()
    if raw_docs:
        retriever.add_documents(raw_docs, ids=None)
        logger.info("ParentDoc: indexed %d raw documents", len(raw_docs))

    return retriever


def _get_retriever() -> _LC_PDR:
    global _cached_retriever
    if _cached_retriever is None:
        _cached_retriever = _build_parent_doc_retriever()
    return _cached_retriever


class ParentDocRetriever:
    """Parent-Document Retriever (small-to-big) using Module 11 LangChain pattern.

    Searches child chunks (400 chars) for precise matching, returns parent
    chunks (2000 chars) for richer surrounding context.

    Uses an in-memory Qdrant instance populated from the same source files
    as the main knowledge base.
    """

    def __init__(self) -> None:
        pass  # index built lazily on first retrieve()

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
            retriever = await asyncio.to_thread(_get_retriever)
            retriever.search_kwargs = {"k": k}
            docs = await asyncio.to_thread(retriever.invoke, query)
            results = [
                ChunkResult(
                    content=doc.page_content,
                    score=1.0 / (i + 1),
                    source=doc.metadata.get("source", "parent_doc"),
                    metadata=doc.metadata,
                )
                for i, doc in enumerate(docs[:k])
            ]
            logger.debug("ParentDoc retrieval: query=%r → %d results", query[:60], len(results))
            return results
        except Exception:
            logger.warning("ParentDoc failed — falling back to dense retrieval", exc_info=True)
            from src.retrieval.dense_retriever import DenseRetriever
            return await DenseRetriever().retrieve(query, k=k)

    def get_langchain_retriever(self, k: int = 10) -> _LC_PDR:
        retriever = _get_retriever()
        retriever.search_kwargs = {"k": k}
        return retriever
