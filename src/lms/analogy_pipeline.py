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
    mechanism_diagram_props: dict
    audio_url: str
    audio_local_path: str
    # final
    version: int
    error: str


# ── Animation props prompt ────────────────────────────────────────────────────

_ANIMATION_SCENE_PROMPT = """\
You are a visual storyteller creating a Remotion animation scene for an AI/ML concept analogy.
Output valid JSON only. The scene VISUALIZES the real-world analogy as a vivid metaphor.

RULES:
- Characters represent technical components through their ANALOGY ROLE (not their tech name)
- Each character = exactly one technical component
- The keyItem = the thing being transformed/transferred (the concept's central output)
- The scene captures ONE MOMENT that reveals the concept's mechanism — not a story arc
- concept_bridge MUST include the 1:1 mapping: "[scene] represents [concept] because [A]==[tech1], [B]==[tech2]"
- NEVER use kitchen/chef/cooking domains
- Match characters/setting to the analogy domain (detective, ocean, astronomy, hospital, music, sports, etc.)

OUTPUT:
{
  "type": "analogy_scene",
  "props": {
    "concept": "<concept name>",
    "emoji": "<single emoji>",
    "accentColor": "<hex color matching mood>",
    "scene": {
      "setting": "<specific vivid place matching analogy domain ≤15 words>",
      "characters": [
        {"emoji": "<emoji>", "label": "<real-world role ≤12 chars>", "description": "<what AI/ML component this represents>"},
        {"emoji": "<emoji>", "label": "<real-world role ≤12 chars>", "description": "<what AI/ML component this represents>"}
      ],
      "keyItem": {"emoji": "<emoji>", "label": "<the transformed output ≤10 chars>"},
      "items": [],
      "act1": "<Setup: characters at their positions, situation established ≤10 words>",
      "act2": "<Exchange: they meet at center, keyItem appears, interaction ≤10 words>",
      "act3": "<Result: transformation/outcome complete, characters return ≤10 words>",
      "concept_bridge": "<[scene element A] = [tech component 1], [scene element B] = [tech component 2] → shows [concept mechanism]>"
    },
    "keywords": ["<key tech term 1>", "<key tech term 2>", "<key tech term 3>"]
  }
}
"""

_MECHANISM_DIAGRAM_PROMPT = """\
You are a senior software architect creating a precise technical diagram for an AI/ML concept.
Think like a developer explaining to another developer — show components, data flows, transformations.
Respond with valid JSON matching the schema below.

DIAGRAM QUALITY RULES:
1. Nodes represent REAL technical components (not vague concepts) — e.g., "Token IDs", "Embedding Matrix", "Softmax Layer", "Vector DB", "HTTP Request"
2. Edges show WHAT FLOWS between components — label edges with the data/signal being passed (e.g., "token IDs", "768-dim vectors", "similarity scores")
3. Use the FULL 6-column grid — spread nodes across columns 0-5 to show pipeline flow left→right
4. Row 0 = input/source layer, Row 1 = processing/core layer, Row 2 = output/result layer
5. Exactly 3 steps — each step reveals a logical stage of the process
6. Captions are developer-grade: mention specific formats, shapes, operations (e.g., "Query vector (768-dim) compared against all key vectors using dot product")
7. Node colors: #7c3aed=AI/model components, #0891b2=data/vectors, #d97706=scores/weights, #059669=output/results, #dc2626=user/input

OUTPUT JSON:
{
  "type": "mechanism_diagram",
  "props": {
    "concept": "<concept name>",
    "title": "How <Concept> Works",
    "accentColor": "<primary hex color>",
    "nodes": [
      {"id": "<snake_case_id>", "label": "<technical 1-3 word label>", "emoji": "<relevant emoji>", "col": <0-5>, "row": <0-2>, "color": "<hex>"}
    ],
    "edges": [
      {"from": "<id>", "to": "<id>", "label": "<what data flows: 1-3 words>"}
    ],
    "steps": [
      {"nodes": ["<id1>", "<id2>"], "caption": "<developer-grade explanation of this stage, ≤18 words>"},
      {"nodes": ["<id3>", "<id4>"], "caption": "<developer-grade explanation, ≤18 words>"},
      {"nodes": ["<id5>", "<id6>"], "caption": "<developer-grade explanation of output/result, ≤18 words>"}
    ]
  }
}
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


def _load_analogy_seed(concept: str) -> str:
    """Load a pre-seeded analogy hint for this concept, if available."""
    seeds_path = _PROJECT_ROOT / "data" / "analogy_seeds.json"
    if not seeds_path.exists():
        return ""
    try:
        with open(seeds_path) as f:
            seeds = json.load(f)
        seed = seeds.get(concept) or seeds.get(concept.lower())
        if not seed:
            return ""
        analogy = seed.get("analogy", "")
        domain = seed.get("domain", "")
        setting = seed.get("scene_setting", "")
        if analogy:
            return (
                f"\n\n## ANALOGY HINT (from creative analogy expert — use this as your story foundation):\n"
                f"Domain: {domain}\n"
                f"Scene: {setting}\n"
                f"Story seed: {analogy}\n"
                f"Expand this into a complete, vivid micro-story. Keep the domain and characters."
            )
    except Exception:
        pass
    return ""


async def analogy_generator_node(state: BytePipelineState) -> dict:
    """2-step analogy generation: research the mechanism → generate world-class content.

    Step 1 (GPT-4o): Research what the concept actually DOES mechanically.
                     Find the perfect everyday analogy that mirrors the mechanism.
    Step 2 (GPT-4o): Generate the full byte content using that research.
    """
    from src.config import get_settings
    from src.llm import get_async_openai
    from src.retrieval.dense_retriever import DenseRetriever

    cfg = get_settings()
    client = get_async_openai()
    topic_name = state["topic_name"]
    concept = state["concept"]

    # ── Retrieval ─────────────────────────────────────────────────────────────
    query = f"{topic_name}: {concept}"
    retriever = DenseRetriever()
    try:
        chunks = await retriever.retrieve(query, k=10)
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

    # ── Step 1: Research the mechanism ────────────────────────────────────────
    research_prompt = f"""Concept: {concept}
Topic: {topic_name}

Source material:
{context_str[:2500]}

As a master teacher, answer these 3 questions in 4-6 sentences total:
1. What does {concept} actually DO step-by-step mechanically? (not "what is it" — HOW does it work internally?)
2. What is the single best everyday thing that works by the EXACT same mechanism? (phone autocomplete, Google Maps, a doctor, etc.)
3. What is the precise 1:1 mapping — [technical component A] = [analogy element X], [component B] = [element Y]?

Your goal: find an analogy so accurate that a developer would call it technically correct AND a 10-year-old would immediately get it."""

    try:
        research_resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a master teacher who specializes in finding perfect mechanism-revealing analogies. "
                        "You always explain HOW things work, not just what they are. "
                        "Your analogies are technically precise AND immediately understandable by anyone aged 5-75."
                    ),
                },
                {"role": "user", "content": research_prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        research = research_resp.choices[0].message.content or ""
        logger.info("analogy_pipeline: research step complete for %s", concept)
    except Exception:
        logger.warning("analogy_pipeline: research step failed, continuing without", exc_info=True)
        research = ""

    # ── Step 2: Generate full byte content ────────────────────────────────────
    seed_hint = _load_analogy_seed(concept)

    user_msg = (
        f"Topic: {topic_name}\n"
        f"Concept: {concept}"
        f"{seed_hint}\n\n"
        f"## Mechanism research (build your analogy FROM this — do not ignore it):\n{research}\n\n"
        f"## Retrieved course context:\n{context_str[:1500]}"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _BYTE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=800,
        temperature=0.65,
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
    image_prompt = state.get("image_prompt", "")

    try:
        url, local_path = await generate_poster(concept, analogy, image_prompt=image_prompt or None)
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
    """Generate Remotion visual scene animation props JSON for the byte card."""
    from src.config import get_settings
    from src.llm import get_async_openai

    cfg = get_settings()
    client = get_async_openai()
    concept = state["concept"]
    analogy = state.get("analogy", "")
    emoji = state.get("emoji", "🧠")

    # Load seed for scene domain guidance
    seed_hint = _load_analogy_seed(concept)
    seed_info = ""
    if seed_hint:
        seeds_path = _PROJECT_ROOT / "data" / "analogy_seeds.json"
        try:
            with open(seeds_path) as f:
                seeds = json.load(f)
            seed = seeds.get(concept) or seeds.get(concept.lower()) or {}
            c1 = seed.get("character1", {})
            c2 = seed.get("character2", {})
            i1 = seed.get("item1", {})
            i2 = seed.get("item2", {})
            setting = seed.get("scene_setting", "")
            domain = seed.get("domain", "")
            if c1 or setting:
                seed_info = (
                    f"\nSEED SCENE GUIDANCE (use these characters/items/setting):"
                    f"\n  Domain: {domain}"
                    f"\n  Setting: {setting}"
                    f"\n  Character 1: {c1.get('emoji','')} {c1.get('label','')} — {c1.get('description','')}"
                    f"\n  Character 2: {c2.get('emoji','')} {c2.get('label','')} — {c2.get('description','')}"
                    f"\n  Item 1: {i1.get('emoji','')} {i1.get('label','')}"
                    f"\n  Item 2: {i2.get('emoji','')} {i2.get('label','')}"
                )
        except Exception:
            pass

    user_msg = f"Concept: {concept}\nAnalogy: {analogy[:300]}\nEmoji: {emoji}{seed_info}"

    try:
        resp = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=[
                {"role": "system", "content": _ANIMATION_SCENE_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=900,
            temperature=0.5,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        animation_props = json.loads(raw)
    except Exception:
        logger.warning("analogy_pipeline: animation_props generation failed", exc_info=True)
        animation_props = {
            "type": "analogy_scene",
            "props": {
                "concept": concept,
                "emoji": emoji,
                "accentColor": "#8b5cf6",
                "scene": {
                    "setting": "",
                    "characters": [],
                    "items": [],
                    "act1": "",
                    "act2": "",
                    "act3": "",
                    "concept_bridge": analogy[:200],
                },
                "keywords": [],
            },
        }

    logger.info("analogy_pipeline: animation_props type=%s", animation_props.get("type"))
    return {"animation_props": animation_props}


async def mechanism_diagram_agent_node(state: BytePipelineState) -> dict:
    """Generate architect-grade animated mechanism diagram props JSON."""
    from src.config import get_settings
    from src.llm import get_async_openai

    get_settings()
    client = get_async_openai()
    concept = state["concept"]
    analogy = state.get("analogy", "")
    explanation = state.get("explanation", "")

    # Step 1: Think through the architecture
    think_prompt = f"""Concept: {concept}
Analogy: {analogy[:200]}
Explanation: {explanation[:400]}

As a software architect, briefly outline:
1. What are the 4-6 key technical components involved?
2. What data/signals flow between them?
3. What are the 3 logical stages of the process?
Keep it brief — this is planning notes only."""

    try:
        think_resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior software architect. Think through technical component diagrams concisely."},
                {"role": "user", "content": think_prompt},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        thinking = think_resp.choices[0].message.content or ""
    except Exception:
        thinking = ""

    # Step 2: Generate the diagram JSON
    user_msg = f"Concept: {concept}\nExplanation: {explanation[:400]}\nArchitecture notes:\n{thinking}"

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _MECHANISM_DIAGRAM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=1000,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        mechanism_diagram_props = json.loads(raw)
    except Exception:
        logger.warning("analogy_pipeline: mechanism_diagram generation failed", exc_info=True)
        mechanism_diagram_props = {"type": "none"}

    logger.info("analogy_pipeline: mechanism_diagram type=%s", mechanism_diagram_props.get("type"))
    return {"mechanism_diagram_props": mechanism_diagram_props}


# ── Public audio dir ──────────────────────────────────────────────────────────
_PUBLIC_AUDIO_DIR = _PROJECT_ROOT / "zizi-lms" / "public" / "generated" / "audio"


async def tts_audio_node(state: BytePipelineState) -> dict:
    """Generate TTS narration audio for the concept analogy (OpenAI TTS-1)."""
    import re

    from src.config import get_settings
    from src.llm import get_async_openai

    cfg = get_settings()  # noqa: F841 — ensures settings loaded
    client = get_async_openai()
    concept = state["concept"]
    analogy = state.get("analogy", "")

    if not analogy:
        return {"audio_url": "", "audio_local_path": ""}

    # Keep narration concise: concept name + first 600 chars of analogy
    narration = f"{concept}. {analogy[:600]}"

    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=narration,
        )

        slug = re.sub(r"[^a-z0-9]+", "_", concept.lower())[:40]
        audio_filename = f"{state['topic_id'][:8]}_{slug}.mp3"

        _PUBLIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        audio_path = _PUBLIC_AUDIO_DIR / audio_filename
        audio_path.write_bytes(response.content)

        audio_url = f"/generated/audio/{audio_filename}"
        logger.info("tts_audio_node: generated audio %s", audio_url)
        return {"audio_url": audio_url, "audio_local_path": str(audio_path)}
    except Exception:
        logger.warning("tts_audio_node: TTS generation failed", exc_info=True)
        return {"audio_url": "", "audio_local_path": ""}


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
        "mechanism_diagram_props": state.get("mechanism_diagram_props", {}),
        "sources": state.get("sources", []),
        "audio_url": state.get("audio_url", ""),
        "audio_local_path": state.get("audio_local_path", ""),
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
    """Fan out to image, animation, mechanism diagram, and TTS audio agents in parallel."""
    return [
        Send("image_agent", state),
        Send("animation_props_agent", state),
        Send("mechanism_diagram_agent", state),
        Send("tts_audio_node", state),
    ]


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_analogy_graph() -> CompiledStateGraph:
    """Build and compile the analogy byte pipeline graph."""
    builder: StateGraph = StateGraph(BytePipelineState)

    builder.add_node("check_cache", check_cache_node)
    builder.add_node("analogy_generator", analogy_generator_node)
    builder.add_node("image_agent", image_agent_node)
    builder.add_node("animation_props_agent", animation_props_agent_node)
    builder.add_node("mechanism_diagram_agent", mechanism_diagram_agent_node)
    builder.add_node("tts_audio_node", tts_audio_node)
    builder.add_node("persist", persist_node)

    builder.add_edge(START, "check_cache")
    builder.add_conditional_edges("check_cache", route_after_cache)
    builder.add_conditional_edges(
        "analogy_generator",
        fan_out_after_analogy,
        ["image_agent", "animation_props_agent", "mechanism_diagram_agent", "tts_audio_node"],
    )
    builder.add_edge("image_agent", "persist")
    builder.add_edge("animation_props_agent", "persist")
    builder.add_edge("mechanism_diagram_agent", "persist")
    builder.add_edge("tts_audio_node", "persist")
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
        "mechanism_diagram_props": {},
        "audio_url": "",
        "audio_local_path": "",
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
        "mechanism_diagram_props": final_state.get("mechanism_diagram_props", {}),
        "sources": final_state.get("sources", []),
        "audio_url": final_state.get("audio_url", ""),
        "audio_local_path": final_state.get("audio_local_path", ""),
        "version": 1,
        "is_active": 1,
        "error": final_state.get("error", ""),
    }
