"""LangGraph multi-agent pipeline for byte-sized analogy generation.

Flow:
  check_cache → [hit]  → END  (returns cached row)
             → [miss]  → analogy_generator
                           → fan-out (Send):
                               image_agent
                               animation_props_agent
                           → persist → END

The analogy_generator uses the same system prompt as ByteGenerator._BYTE_SYSTEM
and the same KG+Dense retrieval pattern (k=8).

Parallel image + animation fan-out uses LangGraph's Send primitive.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal

from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from src.lms.byte_generator import _BYTE_SYSTEM

logger = logging.getLogger(__name__)

# ── Public output dir for Next.js static serving ──────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_PUBLIC_IMAGES_DIR = _PROJECT_ROOT / "zizi-lms" / "public" / "generated" / "images"


# ── State ─────────────────────────────────────────────────────────────────────

class BytePipelineState(TypedDict):
    topic_id: str
    topic_name: str
    concept: str
    force_regenerate: bool
    db_path: str
    # cache
    cache_hit: bool
    cached_row: dict
    # analogy agent outputs
    analogy: str
    explanation: str
    why_it_matters: str
    emoji: str
    image_prompt: str
    sources: list[str]
    # parallel agent outputs
    image_url: str
    image_local_path: str
    animation_props: dict
    # final
    version: int
    error: str


# ── Animation props prompt ────────────────────────────────────────────────────

_ANIMATION_SYSTEM = """\
You generate Remotion animation props for a byte-sized learning card.

Given a concept and analogy, output STRICT JSON in ONE of these two formats:

FORMAT 1 — AnalogyReveal (for abstract/conceptual topics):
{"type": "analogy_reveal", "props": {"concept": "...", "analogy": "...", "emoji": "...", "accentColor": "#8b5cf6", "keywords": ["word1", "word2", "word3"]}}

FORMAT 2 — ConceptFlow (for process/pipeline topics like "RAG pipeline", "agent loop", "LangGraph state"):
{"type": "concept_flow", "props": {"concept": "...", "nodes": [{"id": "1", "label": "Step 1", "x": 10, "y": 50, "color": "#8b5cf6"}], "edges": [{"fromId": "1", "toId": "2", "label": "→"}], "accentColor": "#22d3ee"}}

x and y are percentages (0-100) of the composition width/height.
Max 5 nodes for ConceptFlow. Labels ≤ 20 chars.
"""


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def check_cache_node(state: BytePipelineState) -> dict:
    """Check SQLite for an existing active byte. Short-circuit if found."""
    from src.lms.analogy_store import get_active_byte

    if state.get("force_regenerate"):
        logger.info("analogy_pipeline: force_regenerate=True — skipping cache")
        return {"cache_hit": False, "cached_row": {}}

    db_path = state.get("db_path", "data/analogies.db")
    row = await get_active_byte(state["topic_id"], state["concept"], db_path=db_path)
    if row:
        logger.info(
            "analogy_pipeline: cache HIT topic=%s concept=%s version=%s",
            state["topic_id"],
            state["concept"],
            row.get("version"),
        )
        return {"cache_hit": True, "cached_row": row}

    logger.info(
        "analogy_pipeline: cache MISS topic=%s concept=%s",
        state["topic_id"],
        state["concept"],
    )
    return {"cache_hit": False, "cached_row": {}}


async def analogy_generator_node(state: BytePipelineState) -> dict:
    """KG+Dense RAG (k=8) → GPT-4o-mini structured JSON analogy."""
    from src.config import get_settings
    from src.llm import get_async_openai
    from src.retrieval.dense_retriever import DenseRetriever

    cfg = get_settings()
    client = get_async_openai()
    topic_name = state["topic_name"]
    concept = state["concept"]

    # Retrieval — same pattern as ByteGenerator._retrieve_chunks
    query = f"{topic_name}: {concept}"
    retriever = DenseRetriever()
    try:
        chunks = await retriever.retrieve(query, k=8)
        kb_chunks = [
            {
                "content": c.content if hasattr(c, "content") else c["content"],
                "source": c.source if hasattr(c, "source") else c["source"],
            }
            for c in chunks
        ]
    except Exception:
        logger.warning("analogy_pipeline: retrieval failed", exc_info=True)
        kb_chunks = []

    context_str = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['content']}" for c in kb_chunks
    ) or "No context found."
    sources = list({c["source"] for c in kb_chunks})

    user_msg = (
        f"Topic: {topic_name}\n"
        f"Concept: {concept}\n\n"
        f"## Retrieved course context:\n{context_str}"
    )

    resp = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": _BYTE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=600,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("analogy_pipeline: JSON parse failed, raw=%s", raw[:200])
        data = {}

    logger.info(
        "analogy_pipeline: generated analogy for topic=%s concept=%s",
        state["topic_id"],
        concept,
    )
    return {
        "analogy": data.get("analogy", ""),
        "explanation": data.get("explanation", ""),
        "why_it_matters": data.get("why_it_matters", ""),
        "emoji": data.get("emoji", "🧠"),
        "image_prompt": data.get("image_prompt", ""),
        "sources": sources,
    }


async def image_agent_node(state: BytePipelineState) -> dict:
    """Generate a DALL-E poster and copy to Next.js public directory."""
    from src.tools.image_tool import generate_poster

    concept = state["concept"]
    analogy = state.get("analogy", concept)

    try:
        url, local_path = await generate_poster(concept, analogy)
    except Exception:
        logger.warning("analogy_pipeline: image generation failed", exc_info=True)
        return {"image_url": "", "image_local_path": ""}

    if not local_path:
        return {"image_url": url or "", "image_local_path": ""}

    # Copy to Next.js public directory
    try:
        _PUBLIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        dest_filename = f"{uuid.uuid4().hex}.png"
        dest_path = _PUBLIC_IMAGES_DIR / dest_filename
        shutil.copy2(local_path, dest_path)
        relative_url = f"/generated/images/{dest_filename}"
        logger.info("analogy_pipeline: image copied to %s", dest_path)
        return {"image_url": relative_url, "image_local_path": str(dest_path)}
    except Exception:
        logger.warning("analogy_pipeline: failed to copy image to public dir", exc_info=True)
        return {"image_url": str(local_path), "image_local_path": str(local_path)}


async def animation_props_agent_node(state: BytePipelineState) -> dict:
    """Generate Remotion animation props JSON for the byte card."""
    from src.config import get_settings
    from src.llm import get_async_openai

    cfg = get_settings()
    client = get_async_openai()
    concept = state["concept"]
    analogy = state.get("analogy", "")
    emoji = state.get("emoji", "🧠")

    user_msg = (
        f"Concept: {concept}\n"
        f"Analogy: {analogy}\n"
        f"Emoji: {emoji}\n\n"
        "Generate the Remotion animation props JSON for this concept."
    )

    try:
        resp = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=[
                {"role": "system", "content": _ANIMATION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=400,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        animation_props = json.loads(raw)
    except Exception:
        logger.warning("analogy_pipeline: animation_props generation failed", exc_info=True)
        animation_props = {
            "type": "analogy_reveal",
            "props": {
                "concept": concept,
                "analogy": analogy,
                "emoji": emoji,
                "accentColor": "#8b5cf6",
                "keywords": [],
            },
        }

    logger.info("analogy_pipeline: animation_props type=%s", animation_props.get("type"))
    return {"animation_props": animation_props}


async def persist_node(state: BytePipelineState) -> dict:
    """Save completed byte to SQLite via analogy_store."""
    from src.lms.analogy_store import save_byte

    db_path = state.get("db_path", "data/analogies.db")
    data = {
        "analogy": state.get("analogy", ""),
        "explanation": state.get("explanation", ""),
        "why_it_matters": state.get("why_it_matters", ""),
        "emoji": state.get("emoji", "🧠"),
        "image_prompt": state.get("image_prompt", ""),
        "image_url": state.get("image_url", ""),
        "image_local_path": state.get("image_local_path", ""),
        "animation_props": state.get("animation_props", {}),
        "sources": state.get("sources", []),
    }

    try:
        row_id = await save_byte(
            topic_id=state["topic_id"],
            concept=state["concept"],
            data=data,
            db_path=db_path,
        )
        logger.info("analogy_pipeline: persisted byte row_id=%s", row_id)
    except Exception:
        logger.error("analogy_pipeline: persist failed", exc_info=True)

    return {}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_cache(state: BytePipelineState) -> str | list:
    """If cache hit, end; otherwise run the analogy generator."""
    if state.get("cache_hit"):
        return END
    return "analogy_generator"


def fan_out_after_analogy(state: BytePipelineState) -> list[Send]:
    """Fan out to image and animation agents in parallel."""
    return [
        Send("image_agent", state),
        Send("animation_props_agent", state),
    ]


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_analogy_graph() -> CompiledStateGraph:
    """Build and compile the analogy byte pipeline graph."""
    builder: StateGraph = StateGraph(BytePipelineState)

    builder.add_node("check_cache", check_cache_node)
    builder.add_node("analogy_generator", analogy_generator_node)
    builder.add_node("image_agent", image_agent_node)
    builder.add_node("animation_props_agent", animation_props_agent_node)
    builder.add_node("persist", persist_node)

    builder.add_edge(START, "check_cache")
    builder.add_conditional_edges("check_cache", route_after_cache)
    builder.add_conditional_edges("analogy_generator", fan_out_after_analogy, ["image_agent", "animation_props_agent"])
    builder.add_edge("image_agent", "persist")
    builder.add_edge("animation_props_agent", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


# ── Public entry point ────────────────────────────────────────────────────────

async def run_byte_pipeline(
    topic_id: str,
    topic_name: str,
    concept: str,
    force_regenerate: bool = False,
    db_path: str = "data/analogies.db",
) -> dict:
    """Run the full byte pipeline and return the result dict.

    Returns the active byte dict (from cache or freshly generated).
    Includes is_active=1.
    """
    from src.lms.analogy_store import get_active_byte, init_db

    await init_db(db_path)

    initial_state: BytePipelineState = {
        "topic_id": topic_id,
        "topic_name": topic_name,
        "concept": concept,
        "force_regenerate": force_regenerate,
        "db_path": db_path,
        "cache_hit": False,
        "cached_row": {},
        "analogy": "",
        "explanation": "",
        "why_it_matters": "",
        "emoji": "🧠",
        "image_prompt": "",
        "sources": [],
        "image_url": "",
        "image_local_path": "",
        "animation_props": {},
        "version": 1,
        "error": "",
    }

    graph = build_analogy_graph()
    final_state: dict[str, Any] = await graph.ainvoke(initial_state)

    # If cache hit, return the cached row enriched with is_active
    if final_state.get("cache_hit") and final_state.get("cached_row"):
        row = final_state["cached_row"]
        row.setdefault("is_active", 1)
        return row

    # Otherwise fetch the freshly persisted row
    row = await get_active_byte(topic_id, concept, db_path=db_path)
    if row:
        row["is_active"] = 1
        return row

    # Fallback: return state fields directly (persist may have failed)
    return {
        "topic_id": topic_id,
        "topic_name": topic_name,
        "concept": concept,
        "analogy": final_state.get("analogy", ""),
        "explanation": final_state.get("explanation", ""),
        "why_it_matters": final_state.get("why_it_matters", ""),
        "emoji": final_state.get("emoji", "🧠"),
        "image_prompt": final_state.get("image_prompt", ""),
        "image_url": final_state.get("image_url", ""),
        "image_local_path": final_state.get("image_local_path", ""),
        "animation_props": final_state.get("animation_props", {}),
        "sources": final_state.get("sources", []),
        "version": 1,
        "is_active": 1,
        "error": final_state.get("error", ""),
    }
