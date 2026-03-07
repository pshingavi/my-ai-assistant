"""Course material ingester — loads AIE9 PDFs, notebooks, and markdown files.

Chunking strategy by source type:
  - PDF:      RecursiveCharacterTextSplitter (512 tokens, 50 overlap)
  - Notebook: Cell-level — pairs markdown explanation + code cell
  - Markdown/Text: Fixed-size (512 words, 50 overlap)

All chunks are tagged with source_type, module, difficulty and stored in the
course_knowledge_base Qdrant collection.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

from src.config import get_settings
from src.llm import embed_texts
from src.memory.qdrant_store import ensure_collection, upsert_chunks

logger = logging.getLogger(__name__)


class CourseIngester:
    """Ingests AIE9 course materials into the KB collection."""

    def __init__(self, collection: str | None = None) -> None:
        self._collection = collection or get_settings().kb_collection

    async def ingest(
        self, source: Path | str, metadata: dict[str, Any] | None = None
    ) -> int:
        source = Path(source)
        metadata = metadata or {}

        suffix = source.suffix.lower()
        if suffix == ".pdf":
            chunks, metas = self._load_pdf(source, metadata)
        elif suffix == ".ipynb":
            chunks, metas = self._load_notebook(source, metadata)
        elif suffix in (".md", ".txt"):
            chunks, metas = self._load_text(source, metadata)
        else:
            logger.warning("Unsupported file type: %s", suffix)
            return 0

        if not chunks:
            return 0

        ensure_collection(self._collection)
        vectors = await embed_texts(chunks)
        return upsert_chunks(self._collection, chunks, vectors, metas)

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_pdf(
        self, path: Path, extra_meta: dict[str, Any]
    ) -> tuple[list[str], list[dict]]:
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.error("pypdf required: uv add pypdf")
            return [], []

        cfg = get_settings()
        reader = PdfReader(str(path))
        full_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
        )
        raw_chunks = splitter.split_text(full_text)
        meta_base = {"source_type": "pdf", "source": path.name, **extra_meta}
        return raw_chunks, [dict(meta_base, chunk_index=i) for i, _ in enumerate(raw_chunks)]

    def _load_notebook(
        self, path: Path, extra_meta: dict[str, Any]
    ) -> tuple[list[str], list[dict]]:
        nb = json.loads(path.read_text(encoding="utf-8"))
        cells = nb.get("cells", [])

        chunks, metas = [], []
        pending_markdown = ""
        meta_base = {"source_type": "notebook", "source": path.name, **extra_meta}

        for i, cell in enumerate(cells):
            ctype = cell.get("cell_type", "")
            src = "".join(cell.get("source", []))

            if ctype == "markdown":
                pending_markdown = src
            elif ctype == "code" and src.strip():
                # Pair the preceding markdown with this code cell
                paired = f"{pending_markdown}\n\n```python\n{src}\n```" if pending_markdown else f"```python\n{src}\n```"
                chunks.append(paired)
                metas.append(dict(meta_base, chunk_index=i))
                pending_markdown = ""

        # Any trailing markdown without a following code cell
        if pending_markdown:
            chunks.append(pending_markdown)
            metas.append(dict(meta_base, chunk_index=len(chunks)))

        return chunks, metas

    def _load_text(
        self, path: Path, extra_meta: dict[str, Any]
    ) -> tuple[list[str], list[dict]]:
        cfg = get_settings()
        text = path.read_text(encoding="utf-8", errors="ignore")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
        )
        raw_chunks = splitter.split_text(text)
        source_type = "markdown" if path.suffix == ".md" else "text"
        meta_base = {"source_type": source_type, "source": path.name, **extra_meta}
        return raw_chunks, [dict(meta_base, chunk_index=i) for i, _ in enumerate(raw_chunks)]
