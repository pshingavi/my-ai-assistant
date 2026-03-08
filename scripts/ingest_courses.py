"""Bulk ingest AIE9 course materials into the knowledge base.

Ingests PDFs, notebooks, and markdown from selected Learn-AI-Engineering modules.

Usage:
    uv run python scripts/ingest_courses.py
    uv run python scripts/ingest_courses.py --modules 04,05,11
    uv run python scripts/ingest_courses.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# Path to Learn-AI-Engineering repo (adjust if needed)
COURSE_BASE = Path(os.environ.get(
    "COURSE_BASE",
    str(Path(__file__).parent.parent.parent / "Learn-AI-Engineering"),
))

# Modules to ingest (subset chosen for relevance + manageability)
DEFAULT_MODULES = [
    "02_Dense_Vector_Retrieval",
    "03_The_Agent_Loop",
    "04_Agentic_RAG_From_Scratch",
    "05_Multi_Agent_with_LangGraph",
    "06_Agent_Memory",
    "09_Synthetic_Data_Generation_and_LangSmith",
    "10_Evaluating_RAG_With_Ragas",
    "11_Advanced_Retrieval",
]

SUPPORTED_SUFFIXES = {".pdf", ".ipynb", ".md"}

# Directories to skip entirely
SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules", ".ipynb_checkpoints"}

# File name patterns to skip
SKIP_NAMES = {
    "uv.lock", ".gitignore", "pyproject.toml", "README.md",
    "top_level.txt", "entry_points.txt", "vendor.txt",
    "ThirdPartyNotices.txt", "__not_in_default_pythonpath.txt",
}


def collect_files(modules: list[str]) -> list[tuple[Path, dict]]:
    """Collect course files (PDFs, notebooks, selected markdown) from chosen modules.

    Skips .venv, __pycache__, package metadata, and other non-course content.
    """
    files = []
    for mod in modules:
        mod_path = COURSE_BASE / mod
        if not mod_path.exists():
            logger.warning("Module not found: %s", mod_path)
            continue
        mod_num = mod.split("_")[0]
        for f in sorted(mod_path.rglob("*")):
            # Skip hidden directories and known noise dirs
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            if not f.is_file():
                continue
            if f.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if f.name in SKIP_NAMES:
                continue
            # Skip tiny files (< 200 bytes) — likely empty stubs
            if f.stat().st_size < 200:
                continue
            meta = {
                "module": mod,
                "module_number": mod_num,
                "difficulty": _infer_difficulty(mod_num),
            }
            files.append((f, meta))
    return files


def _infer_difficulty(mod_num: str) -> str:
    n = int(mod_num) if mod_num.isdigit() else 5
    if n <= 3:
        return "beginner"
    if n <= 7:
        return "intermediate"
    return "advanced"


# How course modules build on each other.
# (from_module → [to_modules])  — extend when new modules are added.
_MODULE_RELATIONS: dict[str, list[str]] = {
    "02_Dense_Vector_Retrieval": [
        "04_Agentic_RAG_From_Scratch",
        "11_Advanced_Retrieval",
    ],
    "03_The_Agent_Loop": [
        "04_Agentic_RAG_From_Scratch",
        "05_Multi_Agent_with_LangGraph",
    ],
    "04_Agentic_RAG_From_Scratch": [
        "06_Agent_Memory",
        "10_Evaluating_RAG_With_Ragas",
        "11_Advanced_Retrieval",
    ],
    "05_Multi_Agent_with_LangGraph": [
        "03_The_Agent_Loop",
        "06_Agent_Memory",
    ],
    "09_Synthetic_Data_Generation_and_LangSmith": [
        "10_Evaluating_RAG_With_Ragas",
    ],
    "10_Evaluating_RAG_With_Ragas": [
        "11_Advanced_Retrieval",
    ],
    "11_Advanced_Retrieval": [
        "02_Dense_Vector_Retrieval",
    ],
}

# Predefined topic metadata for each course module.
# Extend this dict when new cohort modules are added.
_MODULE_TOPICS: dict[str, dict] = {
    "02_Dense_Vector_Retrieval": {
        "name": "Dense Vector Retrieval",
        "description": "Semantic search using dense vector embeddings and cosine similarity stored in Qdrant.",
        "concepts": ["embeddings", "cosine similarity", "Qdrant", "vector search", "text-embedding-3-small"],
        "module_number": "02",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/02_Dense_Vector_Retrieval",
    },
    "03_The_Agent_Loop": {
        "name": "The Agent Loop",
        "description": "ReAct pattern: AI agents reason and act in a loop by calling tools and reflecting on results.",
        "concepts": ["ReAct", "tool calling", "agent reasoning", "planning", "LLM loop"],
        "module_number": "03",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/03_The_Agent_Loop",
    },
    "04_Agentic_RAG_From_Scratch": {
        "name": "Agentic RAG",
        "description": "Building Retrieval-Augmented Generation with agentic decision-making and conditional retrieval steps.",
        "concepts": ["RAG", "chunking", "document loading", "conditional logic", "retrieval augmentation"],
        "module_number": "04",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/04_Agentic_RAG_From_Scratch",
    },
    "05_Multi_Agent_with_LangGraph": {
        "name": "Multi-Agent LangGraph",
        "description": "Orchestrating multiple specialized AI agents using LangGraph state machines and conditional edges.",
        "concepts": ["LangGraph", "multi-agent", "state machine", "conditional edges", "graph orchestration"],
        "module_number": "05",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/05_Multi_Agent_with_LangGraph",
    },
    "06_Agent_Memory": {
        "name": "Agent Memory",
        "description": "Persistent memory systems for AI agents: episodic, semantic, and procedural memory.",
        "concepts": ["episodic memory", "vector memory", "conversation history", "long-term memory", "memory retrieval"],
        "module_number": "06",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/06_Agent_Memory",
    },
    "09_Synthetic_Data_Generation_and_LangSmith": {
        "name": "Synthetic Data & LangSmith",
        "description": "Generating evaluation datasets synthetically and tracing AI pipelines with LangSmith observability.",
        "concepts": ["LangSmith", "tracing", "observability", "synthetic data", "evaluation datasets"],
        "module_number": "09",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/09_Synthetic_Data_Generation_and_LangSmith",
    },
    "10_Evaluating_RAG_With_Ragas": {
        "name": "RAG Evaluation with RAGAS",
        "description": "Measuring RAG quality using RAGAS: context recall, faithfulness, and answer relevancy metrics.",
        "concepts": ["RAGAS", "faithfulness", "context recall", "answer relevancy", "evaluation metrics"],
        "module_number": "10",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/10_Evaluating_RAG_With_Ragas",
    },
    "11_Advanced_Retrieval": {
        "name": "Advanced Retrieval",
        "description": "HyDE, reranking, and knowledge graph retrieval for bridging the semantic gap in RAG.",
        "concepts": ["HyDE", "reranking", "knowledge graph", "multi-hop retrieval", "hypothetical documents"],
        "module_number": "11",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/11_Advanced_Retrieval",
    },
}


async def _build_course_kg(modules: list[str]) -> None:
    """Add course module topic nodes and edges to the Knowledge Graph."""
    import uuid
    from src.llm import embed_texts
    from src.memory.topic_graph import TopicNode, get_topic_graph

    kg = get_topic_graph()
    added = 0

    # ── Pass 1: add missing nodes ─────────────────────────────────────────────
    for mod in modules:
        info = _MODULE_TOPICS.get(mod)
        if not info:
            continue
        if any(kg.graph.nodes[nid]["data"].name == info["name"] for nid in kg.graph.nodes):
            continue  # already present
        try:
            vectors = await embed_texts([f"{info['name']}: {info['description']}"])
            node = TopicNode(
                id=str(uuid.uuid4()),
                name=info["name"],
                description=info["description"],
                concepts=info["concepts"],
                embedding=vectors[0],
                module_number=info.get("module_number", ""),
                source_url=info.get("source_url", ""),
            )
            kg.add_topic(node)  # no related_to — we wire edges explicitly below
            added += 1
        except Exception:
            logger.warning("Failed to add KG node for module %s", mod, exc_info=True)

    # ── Pass 2: wire edges between modules ───────────────────────────────────
    edges_added = 0
    for mod, targets in _MODULE_RELATIONS.items():
        from_info = _MODULE_TOPICS.get(mod)
        if not from_info:
            continue
        for target_mod in targets:
            to_info = _MODULE_TOPICS.get(target_mod)
            if not to_info:
                continue
            if kg.connect_by_name(from_info["name"], to_info["name"]):
                edges_added += 1
    if edges_added:
        kg.save()

    logger.info("Course KG: added %d nodes, %d edges. Total: %s", added, edges_added, kg.stats())


async def ingest_all(modules: list[str], dry_run: bool = False) -> None:
    from src.config import get_settings
    from src.ingestion.course_ingester import CourseIngester
    from src.memory.qdrant_store import ensure_collection

    cfg = get_settings()
    ensure_collection(cfg.kb_collection)
    ingester = CourseIngester()

    files = collect_files(modules)
    logger.info("Found %d files to ingest across %d modules", len(files), len(modules))

    if dry_run:
        for f, meta in files:
            logger.info("[DRY RUN] %s  →  %s", f.relative_to(COURSE_BASE), meta)
        return

    total_chunks = 0
    for i, (f, meta) in enumerate(files, 1):
        logger.info("[%d/%d] Ingesting: %s", i, len(files), f.name)
        try:
            n = await ingester.ingest(f, meta)
            total_chunks += n
            logger.info("  → %d chunks", n)
        except Exception:
            logger.error("  → FAILED", exc_info=True)

    logger.info("✅ Done! Ingested %d total chunks into '%s'", total_chunks, cfg.kb_collection)

    # Build KG nodes from course module definitions
    logger.info("Building course Knowledge Graph nodes...")
    await _build_course_kg(modules)


def main() -> None:
    global COURSE_BASE
    parser = argparse.ArgumentParser(description="Ingest AIE9 course materials")
    parser.add_argument("--modules", help="Comma-separated module names (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="List files without ingesting")
    parser.add_argument("--course-base", help="Path to Learn-AI-Engineering repo")
    args = parser.parse_args()

    if args.course_base:
        COURSE_BASE = Path(args.course_base)

    if args.modules:
        modules = [m.strip() for m in args.modules.split(",")]
    else:
        modules = DEFAULT_MODULES

    asyncio.run(ingest_all(modules, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
