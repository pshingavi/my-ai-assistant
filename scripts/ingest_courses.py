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
    "01_Vibe_Check",
    "02_Dense_Vector_Retrieval",
    "03_The_Agent_Loop",
    "04_Agentic_RAG_From_Scratch",
    "05_Multi_Agent_with_LangGraph",
    "06_Agent_Memory",
    "07_Deep_Agents",
    "08_Open_DeepResearch",
    "09_Synthetic_Data_Generation_and_LangSmith",
    "10_Evaluating_RAG_With_Ragas",
    "11_Advanced_Retrieval",
    "14_MCP_Connectors",
    "15_LangGraph_Deployments",
    "16_LLM_Servers",
    "17_MCP_A2A",
    "18_Production_RAG_and_Guardrails",
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
    "01_Vibe_Check": ["02_Dense_Vector_Retrieval"],
    "02_Dense_Vector_Retrieval": ["03_The_Agent_Loop", "04_Agentic_RAG_From_Scratch"],
    "03_The_Agent_Loop": ["04_Agentic_RAG_From_Scratch", "05_Multi_Agent_with_LangGraph"],
    "04_Agentic_RAG_From_Scratch": ["05_Multi_Agent_with_LangGraph", "11_Advanced_Retrieval"],
    "05_Multi_Agent_with_LangGraph": ["06_Agent_Memory", "07_Deep_Agents"],
    "06_Agent_Memory": ["07_Deep_Agents", "09_Synthetic_Data_Generation_and_LangSmith"],
    "07_Deep_Agents": ["08_Open_DeepResearch"],
    "08_Open_DeepResearch": ["14_MCP_Connectors"],
    "09_Synthetic_Data_Generation_and_LangSmith": ["10_Evaluating_RAG_With_Ragas"],
    "10_Evaluating_RAG_With_Ragas": ["11_Advanced_Retrieval"],
    "11_Advanced_Retrieval": ["16_LLM_Servers"],
    "14_MCP_Connectors": ["15_LangGraph_Deployments", "17_MCP_A2A"],
    "15_LangGraph_Deployments": ["16_LLM_Servers"],
    "16_LLM_Servers": ["18_Production_RAG_and_Guardrails"],
    "17_MCP_A2A": ["18_Production_RAG_and_Guardrails"],
    "18_Production_RAG_and_Guardrails": [],
}

# Predefined topic metadata for each course module.
# Extend this dict when new cohort modules are added.
_MODULE_TOPICS: dict[str, dict] = {
    "01_Vibe_Check": {
        "name": "AI Engineering Foundations",
        "description": "How LLMs work, tokens, context windows, and the shift from ML to AI engineering.",
        "concepts": [
            "what is an LLM",
            "tokens and tokenisation",
            "context window",
            "prompt engineering basics",
            "temperature and sampling",
            "system prompts",
            "the AI engineering stack",
            "API vs fine-tuning",
            "latency and cost tradeoffs",
        ],
        "module_number": "01",
        "source_url": "",
    },
    "02_Dense_Vector_Retrieval": {
        "name": "Dense Vector Retrieval",
        "description": "Semantic search using dense vector embeddings and cosine similarity stored in Qdrant.",
        "concepts": [
            "what is an embedding",
            "vector spaces and dimensions",
            "semantic similarity vs keyword search",
            "text-embedding-3-small",
            "cosine similarity",
            "dot product distance",
            "Qdrant vector database",
            "collections and payloads",
            "upsert and query flow",
            "HNSW index for fast search",
            "metadata filtering",
            "batch embedding strategy",
        ],
        "module_number": "02",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/02_Dense_Vector_Retrieval",
    },
    "03_The_Agent_Loop": {
        "name": "The Agent Loop",
        "description": "ReAct pattern: AI agents reason and act in a loop by calling tools and reflecting on results.",
        "concepts": [
            "what is an AI agent",
            "the ReAct pattern",
            "tool calling",
            "function definitions and schemas",
            "observation and reflection",
            "termination conditions",
            "system prompts for agents",
            "LangGraph StateGraph",
            "nodes and edges",
            "state and reducers",
            "checkpointing",
            "human-in-the-loop (HITL)",
            "middleware in the loop",
        ],
        "module_number": "03",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/03_The_Agent_Loop",
    },
    "04_Agentic_RAG_From_Scratch": {
        "name": "Agentic RAG",
        "description": "Building Retrieval-Augmented Generation with agentic decision-making and conditional retrieval steps.",
        "concepts": [
            "what is RAG",
            "the retrieval-generation gap",
            "document loading",
            "text splitting strategies",
            "chunk size tradeoffs",
            "chunk overlap",
            "embedding and upserting chunks",
            "retrieval at query time",
            "context window management",
            "grounding vs hallucination",
            "conditional retrieval logic",
            "agentic decision points in RAG",
            "source citation",
        ],
        "module_number": "04",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/04_Agentic_RAG_From_Scratch",
    },
    "05_Multi_Agent_with_LangGraph": {
        "name": "Multi-Agent LangGraph",
        "description": "Orchestrating multiple specialized AI agents using LangGraph state machines and conditional edges.",
        "concepts": [
            "why multiple agents",
            "supervisor pattern",
            "specialized agent roles",
            "agent-to-agent communication",
            "conditional edges in LangGraph",
            "parallel agent execution",
            "fan-out and fan-in",
            "shared state management",
            "error handling across agents",
            "router patterns",
            "subgraph composition",
        ],
        "module_number": "05",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/05_Multi_Agent_with_LangGraph",
    },
    "06_Agent_Memory": {
        "name": "Agent Memory",
        "description": "Persistent memory systems for AI agents: episodic, semantic, and procedural memory.",
        "concepts": [
            "types of memory: episodic semantic procedural",
            "short-term vs long-term memory",
            "conversation history as context",
            "memory limits and truncation",
            "vector memory store",
            "memory retrieval strategies",
            "memory consolidation",
            "forgetting and pruning",
            "memory-augmented generation",
            "Qdrant as memory backend",
        ],
        "module_number": "06",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/06_Agent_Memory",
    },
    "09_Synthetic_Data_Generation": {
        "name": "Synthetic Data & LangSmith",
        "description": "Generating evaluation datasets synthetically and tracing AI pipelines with LangSmith observability.",
        "concepts": [
            "why synthetic data",
            "LLM-generated test sets",
            "RAGAS TestsetGenerator",
            "question-context-answer triples",
            "distribution of question types",
            "LangSmith tracing",
            "observability in LLM apps",
            "run comparisons and diffs",
            "cost and token tracking",
            "feedback and annotation",
        ],
        "module_number": "09",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/09_Synthetic_Data_Generation_and_LangSmith",
    },
    "10_Evaluating_RAG_With_Ragas": {
        "name": "RAG Evaluation with RAGAS",
        "description": "Measuring RAG quality using RAGAS: context recall, faithfulness, and answer relevancy metrics.",
        "concepts": [
            "why evaluate RAG",
            "the evaluation triangle",
            "context recall",
            "faithfulness",
            "answer relevancy",
            "context precision",
            "LLM-as-judge",
            "RAGAS 0.2.x API",
            "SingleTurnSample format",
            "EvaluationDataset",
            "interpreting scores",
            "evaluation-driven improvement",
        ],
        "module_number": "10",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/10_Evaluating_RAG_With_Ragas",
    },
    "11_Advanced_Retrieval": {
        "name": "Advanced Retrieval",
        "description": "HyDE, reranking, and knowledge graph retrieval for bridging the semantic gap in RAG.",
        "concepts": [
            "the semantic gap problem",
            "HyDE hypothetical document embeddings",
            "multi-query retrieval",
            "parent-document retrieval",
            "BM25 keyword search",
            "ensemble retrieval with RRF",
            "Cohere reranking",
            "semantic chunking",
            "knowledge graph retrieval",
            "multi-hop reasoning",
            "retrieval ablation testing",
            "choosing the right retriever",
        ],
        "module_number": "11",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/11_Advanced_Retrieval",
    },
    "07_Deep_Agents": {
        "name": "Deep Agents",
        "description": "Long-running autonomous agents with planning, file-system context, subagent spawning, and long-term memory.",
        "concepts": [
            "what is a deep agent",
            "planning with todo lists",
            "file system as agent context",
            "subagent spawning",
            "long-term memory integration",
            "skills as on-demand capabilities",
            "deep agent vs standard agent",
            "multi-turn task execution",
        ],
        "module_number": "07",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/07_Deep_Agents",
    },
    "08_Open_DeepResearch": {
        "name": "Open DeepResearch",
        "description": "Building an open-source deep research system with LangGraph: parallel search, synthesis, and iterative refinement.",
        "concepts": [
            "what is deep research",
            "parallel web search with LangGraph",
            "research plan generation",
            "iterative query refinement",
            "source synthesis and deduplication",
            "multi-hop research loops",
            "citation grounding",
            "report generation from evidence",
        ],
        "module_number": "08",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/08_Open_DeepResearch",
    },
    "14_MCP_Connectors": {
        "name": "MCP Connectors",
        "description": "Connecting AI agents to external tools and APIs using the Model Context Protocol (MCP) with LangGraph and LangChain adapters.",
        "concepts": [
            "what is MCP (Model Context Protocol)",
            "MCP server and client architecture",
            "connecting to GitHub MCP server",
            "LangChain MCP adapters",
            "tool decorator vs MCP tools",
            "agent with external API tools",
            "stateful agent with MemorySaver",
            "multi-tool orchestration",
        ],
        "module_number": "14",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/14_MCP_Connectors",
    },
    "15_LangGraph_Deployments": {
        "name": "LangGraph Deployments",
        "description": "Serving LangGraph agentic graphs as production APIs using LangGraph Platform and the Remote Graph SDK.",
        "concepts": [
            "LangGraph Platform overview",
            "langgraph dev for local serving",
            "langgraph.json configuration",
            "assistants and graph registration",
            "RemoteGraph SDK client",
            "streaming agent responses",
            "stateful graph deployment",
            "production API patterns for agents",
        ],
        "module_number": "15",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/15_LangGraph_Deployments",
    },
    "16_LLM_Servers": {
        "name": "LLM Servers",
        "description": "Deploying open-source LLMs as inference endpoints using Fireworks AI and building RAG apps on top.",
        "concepts": [
            "open-source LLM deployment",
            "dedicated vs shared inference endpoints",
            "Fireworks AI endpoint setup",
            "OpenAI-compatible API format",
            "embedding endpoints for open models",
            "RAG on open-source LLMs",
            "latency benchmarking endpoints",
            "cost of self-hosted vs API models",
        ],
        "module_number": "16",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/16_LLM_Servers",
    },
    "17_MCP_A2A": {
        "name": "MCP Servers & Agent-to-Agent Protocol",
        "description": "Building MCP servers and enabling agent-to-agent (A2A) communication for multi-agent interoperability.",
        "concepts": [
            "MCP server implementation",
            "agent-to-agent (A2A) protocol",
            "A2A vs MCP: when to use each",
            "agent cards and capabilities discovery",
            "cross-agent task delegation",
            "A2A client-server communication",
            "multi-agent interoperability",
            "protocol-based agent composition",
        ],
        "module_number": "17",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/17_MCP_A2A",
    },
    "18_Production_RAG_and_Guardrails": {
        "name": "Production RAG & Guardrails",
        "description": "Making RAG systems production-ready with guardrails, caching, and LangGraph agent integration.",
        "concepts": [
            "production RAG checklist",
            "guardrails for LLM safety",
            "input and output validation",
            "guardrails hub validators",
            "semantic caching for RAG",
            "LangGraph agent with guardrails",
            "cost reduction via caching",
            "monitoring production LLM apps",
        ],
        "module_number": "18",
        "source_url": "https://github.com/AI-Makerspace/Learn-AI-Engineering/tree/main/18_Production_RAG_and_Guardrails",
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
