"""Zizi Byte LMS — FastAPI bridge on port 8001.

Exposes JSON endpoints consumed by the Next.js frontend (zizi-lms/).
Runs alongside the Chainlit app (port 8000).

Start:
    uv run python api_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve DB path relative to this file so it works regardless of cwd.
_DB_PATH = str(Path(__file__).parent / "data" / "analogies.db")

app = FastAPI(title="Zizi Byte LMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: initialise SQLite analogy store ──────────────────────────────────

@app.on_event("startup")
async def _startup() -> None:
    from src.lms.analogy_store import init_db
    await init_db(_DB_PATH)
    logger.info("analogy_store DB ready at %s", _DB_PATH)


# ── Topic endpoints ────────────────────────────────────────────────────────────

@app.get("/api/topics")
async def list_topics():
    """Return all topics in the KG, sorted by module number."""
    from src.lms.learning_path import get_all_topics
    topics = get_all_topics()
    return {"topics": [asdict(t) for t in topics]}


@app.get("/api/topics/{topic_id}")
async def get_topic(topic_id: str):
    """Return a single topic by its KG node ID."""
    from src.lms.learning_path import get_topic_by_id
    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return asdict(topic)


@app.get("/api/topics/{topic_id}/neighbors")
async def get_neighbors(topic_id: str):
    """Return prerequisite / next / related topics for a given topic."""
    from src.lms.learning_path import get_topic_neighbors
    neighbors = get_topic_neighbors(topic_id)
    return {
        k: [asdict(t) for t in v]
        for k, v in neighbors.items()
    }


@app.get("/api/kg")
async def get_kg():
    """Return the full KG graph (nodes + edges) for D3 rendering."""
    from src.lms.learning_path import get_kg_graph_data
    return get_kg_graph_data()


@app.get("/api/learning-order")
async def learning_order():
    """Return topics in topological learning order."""
    from src.lms.learning_path import get_learning_order
    topics = get_learning_order()
    return {"topics": [asdict(t) for t in topics]}


# ── Byte generation endpoints ──────────────────────────────────────────────────

class ByteRequest(BaseModel):
    topic_id: str
    concept: str


class BuildRequest(BaseModel):
    topic_id: str
    concept: str


@app.post("/api/bytes/generate")
async def generate_byte(req: ByteRequest):
    """Generate a byte-sized analogy-first learning card for one concept.

    Checks the SQLite cache first. If a cached row exists, returns it immediately.
    Otherwise runs the full analogy pipeline (RAG → LLM → image → animation → persist).
    """
    from src.lms.analogy_store import get_active_byte
    from src.lms.analogy_pipeline import run_byte_pipeline
    from src.lms.learning_path import get_topic_by_id

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Fast cache path
    cached = await get_active_byte(req.topic_id, req.concept, db_path=_DB_PATH)
    if cached:
        logger.info("generate_byte: cache hit topic=%s concept=%s", req.topic_id, req.concept)
        return cached

    # Full pipeline
    result = await run_byte_pipeline(
        topic_id=req.topic_id,
        topic_name=topic.name,
        concept=req.concept,
        db_path=_DB_PATH,
    )
    return result


@app.post("/api/bytes/stream")
async def stream_byte(req: ByteRequest):
    """Stream a byte card as SSE for real-time display."""
    from src.lms.learning_path import get_topic_by_id
    from src.lms.byte_generator import ByteGenerator

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    gen = ByteGenerator()

    async def event_generator():
        async for chunk in gen.generate_byte_stream(topic.name, req.concept):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Cache / versioning / warm endpoints ───────────────────────────────────────

@app.get("/api/bytes/cached/{topic_id}/{concept}")
async def get_cached_byte(topic_id: str, concept: str):
    """Return the currently active cached byte for a (topic_id, concept) pair.

    Returns 404 if no cached byte exists.
    """
    from src.lms.analogy_store import get_active_byte

    row = await get_active_byte(topic_id, concept, db_path=_DB_PATH)
    if not row:
        raise HTTPException(status_code=404, detail="No cached byte found")
    return row


class RegenerateRequest(BaseModel):
    topic_id: str
    concept: str


@app.post("/api/bytes/regenerate")
async def regenerate_byte(req: RegenerateRequest):
    """Force-regenerate a byte, bypassing the cache and saving a new version."""
    from src.lms.analogy_pipeline import run_byte_pipeline
    from src.lms.learning_path import get_topic_by_id

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = await run_byte_pipeline(
        topic_id=req.topic_id,
        topic_name=topic.name,
        concept=req.concept,
        force_regenerate=True,
        db_path=_DB_PATH,
    )
    return result


@app.get("/api/bytes/version-history/{topic_id}/{concept}")
async def byte_version_history(topic_id: str, concept: str):
    """Return all historical versions for a (topic_id, concept) pair."""
    from src.lms.analogy_store import get_version_history

    history = await get_version_history(topic_id, concept, db_path=_DB_PATH)
    return {"versions": history}


class WarmRequest(BaseModel):
    topic_ids: list[str] | None = None


async def warm_cache_all(topic_ids: list[str] | None = None) -> None:
    """Background task: pre-generate bytes for all topics and concepts."""
    from src.lms.analogy_pipeline import run_byte_pipeline
    from src.lms.analogy_store import get_active_byte
    from src.lms.learning_path import get_all_topics

    topics = get_all_topics()
    if topic_ids:
        topics = [t for t in topics if t.id in topic_ids]

    logger.info("warm_cache_all: warming %d topics", len(topics))
    for topic in topics:
        for concept in topic.concepts:
            existing = await get_active_byte(topic.id, concept, db_path=_DB_PATH)
            if existing:
                logger.debug("warm_cache_all: already cached %s/%s — skipping", topic.id, concept)
                continue
            try:
                await run_byte_pipeline(topic.id, topic.name, concept, db_path=_DB_PATH)
                logger.info("warm_cache_all: warmed %s/%s", topic.id, concept)
            except Exception as e:
                logger.warning("warm_cache_all: failed %s/%s: %s", topic.id, concept, e)


@app.post("/api/bytes/warm")
async def warm_bytes(req: WarmRequest, background_tasks: BackgroundTasks):
    """Kick off a background job to pre-generate bytes for all (or specified) topics."""
    background_tasks.add_task(warm_cache_all, req.topic_ids)
    return {"status": "started", "topic_ids": req.topic_ids}


@app.get("/api/bytes/warm/status")
async def warm_status():
    """Return counts of pending/running/done/failed warm jobs."""
    from src.lms.analogy_store import get_warm_status

    counts = await get_warm_status(db_path=_DB_PATH)
    return counts


@app.post("/api/bytes/all")
async def generate_all_bytes(req: ByteRequest):
    """Generate bytes for ALL concepts in a topic at once."""
    from src.lms.learning_path import get_topic_by_id
    from src.lms.byte_generator import ByteGenerator

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    gen = ByteGenerator()
    bytes_list = await gen.generate_all_bytes(topic.name, topic.concepts)
    return {"bytes": [asdict(b) for b in bytes_list]}


@app.post("/api/build/generate")
async def generate_build(req: BuildRequest):
    """Generate a Build mode code card for one concept."""
    from src.lms.learning_path import get_topic_by_id
    from src.lms.byte_generator import ByteGenerator

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    gen = ByteGenerator()
    build = await gen.generate_build(topic.name, req.concept)
    return asdict(build)


# ── Analogy image endpoint ─────────────────────────────────────────────────────

class ImageRequest(BaseModel):
    prompt: str
    topic_name: str


@app.post("/api/image/generate")
async def generate_image(req: ImageRequest):
    """Generate a DALL-E analogy illustration for a byte card."""
    from src.tools.image_tool import generate_poster

    url, local_path = await generate_poster(req.topic_name, req.prompt)
    if not url and not local_path:
        raise HTTPException(status_code=500, detail="Image generation failed")
    return {
        "image_url": url,
        "local_path": str(local_path) if local_path else "",
    }


# ── Share / Post endpoint ──────────────────────────────────────────────────────

class ShareRequest(BaseModel):
    topic_id: str
    concept: str = ""
    analogy: str = ""
    image_url: str = ""
    custom_message: str = ""


@app.post("/api/share/create-post")
async def create_post(req: ShareRequest):
    """Trigger the content pipeline to generate a LinkedIn post for a topic."""
    from src.lms.learning_path import get_topic_by_id
    from src.agents.content_pipeline import (
        dedup_check_node,
        retrieve_context_node,
        generate_post_node,
        generate_image_node,
        ingest_post_node,
    )

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    state: dict = {
        "domain": "Generative AI",
        "user_request": req.custom_message or f"create a post about {topic.name}",
        "tavily_topics": [],
        "x_topics": [],
        "selected_topic": f"{topic.name} — {req.concept}" if req.concept else topic.name,
        "topic_description": topic.description,
        "is_duplicate": False,
        "duplicate_reason": "",
        "kb_context": [],
        "linkedin_post": "",
        "image_url": req.image_url or "",  # pre-populate if provided
        "image_local_path": "",
        "analogy_summary": req.analogy or "",
        "concept": req.concept or "",
        "messages": [],
        "error": "",
    }

    state.update(await dedup_check_node(state))
    if state["is_duplicate"]:
        return {"is_duplicate": True, "reason": state["duplicate_reason"]}

    state.update(await retrieve_context_node(state))
    state.update(await generate_post_node(state))
    if not req.image_url:
        state.update(await generate_image_node(state))
    else:
        state["image_url"] = req.image_url
    await ingest_post_node(state)

    return {
        "is_duplicate": False,
        "topic": topic.name,
        "concept": req.concept,
        "post_text": state["linkedin_post"],
        "image_url": state.get("image_url", ""),
        "image_local_path": state.get("image_local_path", ""),
    }


# ── Chat endpoint (SSE streaming, KG+Dense → Cohere → analogy-first) ──────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    conversation_id: str = ""


_CHAT_SYSTEM = """\
You are Zizi, an expert AI engineering educator. \
Your answers MUST be built EXCLUSIVELY from the retrieved course context below. \
Do NOT use any pre-trained knowledge that is not present in the context chunks. \
If the context does not contain enough information, say so explicitly.

RULES:
1. Lead with a single, vivid analogy from everyday life (cooking, sports, music, cinema…) \
   that is inspired by or consistent with what the course material says.
2. Then give the technical explanation using ONLY facts, quotes, and concepts that appear \
   verbatim or clearly implied in the retrieved chunks. Cite the source file in parentheses \
   e.g. (AIE9_Session03_The-Agent-Loop.pdf).
3. If no chunk is directly relevant, say: "My course material has limited coverage of this — \
   here is what I found:" and use only what is in the context.
4. NEVER invent details, steps, or explanations that are not in the retrieved context, \
   even if you know them from pre-training.
5. End with one thought-provoking follow-up question.
6. Be concise but complete — aim for 200–350 words.

## Retrieved course context (your ONLY allowed knowledge source):
{context}
"""

_STEP_TOKEN = "\x00STEP\x00"
_SRC_TOKEN  = "\x00SRCS\x00"
_DONE_TOKEN = "\x00DONE\x00"


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream a grounded analogy-first chat answer via SSE."""
    from src.retrieval.kg_retriever import KGRetriever
    from src.retrieval.dense_retriever import DenseRetriever
    from src.config import get_settings
    from src.llm import get_async_openai
    import asyncio

    cfg = get_settings()

    async def event_stream():
        # ── Step 1: KG + Dense retrieval ──────────────────────────────────────
        yield f"data: {json.dumps({'type': 'step', 'content': '🧠 Knowledge Graph + Dense Retrieval…'})}\n\n"
        try:
            _K = 15
            kg_chunks = await KGRetriever().retrieve(req.message, k=_K)
            dense_raw = await DenseRetriever().retrieve(req.message, k=_K)

            combined: dict[str, dict] = {}
            for c in [*kg_chunks, *dense_raw]:
                key = (c.content if hasattr(c, "content") else c["content"])[:100]
                entry = {
                    "content": c.content if hasattr(c, "content") else c["content"],
                    "score":   c.score   if hasattr(c, "score")   else c["score"],
                    "source":  c.source  if hasattr(c, "source")  else c["source"],
                }
                if key not in combined or entry["score"] > combined[key]["score"]:
                    combined[key] = entry

            # Keep ALL unique chunks — let Cohere rerank decide relevance.
            # Pre-filtering by embedding score loses exact-match docs that score
            # lower than broader KG neighbourhood chunks.
            chunks = list(combined.values())
        except Exception as e:
            chunks = []
            yield f"data: {json.dumps({'type': 'step', 'content': f'⚠️ Retrieval error: {e}'})}\n\n"

        # ── Step 2: Cohere rerank ──────────────────────────────────────────────
        yield f"data: {json.dumps({'type': 'step', 'content': '🎯 Cohere Reranking…'})}\n\n"
        try:
            if cfg.cohere_api_key and chunks:
                from langchain_core.documents import Document
                from langchain_core.retrievers import BaseRetriever
                from langchain_cohere import CohereRerank
                from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever

                class _MemRetriever(BaseRetriever):
                    docs: list[Document]
                    def _get_relevant_documents(self, q, *, run_manager=None):
                        return self.docs

                mem_docs = [
                    Document(page_content=c["content"], metadata={"source": c["source"]})
                    for c in chunks
                ]
                compressor = CohereRerank(model="rerank-v3.5", top_n=8)
                cr = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=_MemRetriever(docs=mem_docs),
                )
                reranked = await asyncio.to_thread(cr.invoke, req.message)
                if reranked:
                    chunks = [
                        {
                            "content": d.page_content,
                            "score":   d.metadata.get("relevance_score", 0.0),
                            "source":  d.metadata.get("source", "unknown"),
                        }
                        for d in reranked
                    ]
        except Exception:
            pass  # fall back to dense results

        # ── Step 3: Build context ──────────────────────────────────────────────
        context_str = "\n\n---\n\n".join(
            f"[Source: {c['source']}, relevance={c['score']:.2f}]\n{c['content']}"
            for c in chunks[:8]
        ) or "No relevant course context found."

        sources = []
        seen: set[str] = set()
        for c in chunks[:8]:
            src = c.get("source", "unknown")
            if src not in seen:
                seen.add(src)
                sources.append({"source": src, "score": round(c["score"], 3)})

        yield f"data: {json.dumps({'type': 'step', 'content': f'📚 {len(chunks)} chunks retrieved — generating answer…'})}\n\n"

        # ── Step 4: Build conversation messages ───────────────────────────────
        system_msg = _CHAT_SYSTEM.format(context=context_str)
        messages = [{"role": "system", "content": system_msg}]
        for h in req.history[-8:]:   # last 8 turns for memory
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": req.message})

        # ── Step 5: Stream LLM answer ─────────────────────────────────────────
        client = get_async_openai()
        stream = await client.chat.completions.create(
            model=cfg.llm_model,
            messages=messages,
            max_tokens=700,
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'type': 'token', 'content': delta.content})}\n\n"

        # ── Step 6: Send sources + done ───────────────────────────────────────
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


# ── P5 Sketch endpoints ────────────────────────────────────────────────────────

class RegenerateWithAnalogyRequest(BaseModel):
    analogy: str | None = None


@app.get("/api/topic/{topic_id}/concept/{concept}/p5sketch")
async def get_p5_sketch(topic_id: str, concept: str):
    """Return the cached p5 sketch or generate a new one."""
    from src.lms.analogy_store import get_active_byte, get_p5_sketch, save_p5_sketch
    from src.lms.learning_path import get_topic_by_id
    from src.lms.p5_generator import P5SketchGenerator
    from src.retrieval.dense_retriever import DenseRetriever

    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Check cache
    cached = await get_p5_sketch(topic_id, concept, db_path=_DB_PATH)
    if cached:
        logger.info("get_p5_sketch: cache HIT topic=%s concept=%s", topic_id, concept)
        return {"sketch_code": cached["sketch_code"], "steps": cached["steps"]}

    # Get analogy from byte cache for context
    byte_row = await get_active_byte(topic_id, concept, db_path=_DB_PATH)
    analogy = byte_row.get("analogy", "") if byte_row else ""

    # Retrieve RAG context
    try:
        retriever = DenseRetriever()
        chunks = await retriever.retrieve(f"{topic.name}: {concept}", k=8)
        rag_context = [
            {
                "content": c.content if hasattr(c, "content") else c["content"],
                "source": c.source if hasattr(c, "source") else c["source"],
            }
            for c in chunks
        ]
    except Exception:
        logger.warning("get_p5_sketch: RAG retrieval failed", exc_info=True)
        rag_context = []

    # Generate
    gen = P5SketchGenerator()
    result = await gen.generate(
        concept=concept,
        analogy=analogy,
        topic_name=topic.name,
        rag_context=rag_context,
    )

    # Persist
    await save_p5_sketch(
        topic_id=topic_id,
        concept=concept,
        sketch_code=result["sketch_code"],
        steps_json=result["steps"],
        analogy=analogy,
        db_path=_DB_PATH,
    )

    return result


@app.post("/api/topic/{topic_id}/concept/{concept}/p5sketch/regenerate")
async def regenerate_p5_sketch(topic_id: str, concept: str, req: RegenerateWithAnalogyRequest):
    """Clear cache and regenerate byte + p5 sketch, optionally with a new analogy."""
    from src.lms.analogy_store import clear_concept_cache, save_p5_sketch
    from src.lms.analogy_pipeline import run_byte_pipeline
    from src.lms.learning_path import get_topic_by_id
    from src.lms.p5_generator import P5SketchGenerator
    from src.retrieval.dense_retriever import DenseRetriever

    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Clear all caches for this concept
    await clear_concept_cache(topic_id, concept, db_path=_DB_PATH)

    # Regenerate the byte (force, so it won't use stale cache)
    byte_result = await run_byte_pipeline(
        topic_id=topic_id,
        topic_name=topic.name,
        concept=concept,
        force_regenerate=True,
        db_path=_DB_PATH,
    )

    # If user provided a specific analogy, override what was saved
    if req.analogy:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute(
                "UPDATE analogies SET analogy=? WHERE topic_id=? AND concept=? AND is_active=1",
                (req.analogy, topic_id, concept)
            )
            await db.commit()
        byte_result["analogy"] = req.analogy
        analogy = req.analogy
    else:
        analogy = byte_result.get("analogy", "")

    # Retrieve RAG context
    try:
        retriever = DenseRetriever()
        chunks = await retriever.retrieve(f"{topic.name}: {concept}", k=8)
        rag_context = [
            {
                "content": c.content if hasattr(c, "content") else c["content"],
                "source": c.source if hasattr(c, "source") else c["source"],
            }
            for c in chunks
        ]
    except Exception:
        rag_context = []

    # Generate new p5 sketch
    gen = P5SketchGenerator()
    sketch_result = await gen.generate(
        concept=concept,
        analogy=analogy,
        topic_name=topic.name,
        rag_context=rag_context,
    )

    await save_p5_sketch(
        topic_id=topic_id,
        concept=concept,
        sketch_code=sketch_result["sketch_code"],
        steps_json=sketch_result["steps"],
        analogy=analogy,
        db_path=_DB_PATH,
    )

    # Also regenerate Claude interaction with the new analogy
    from src.lms.claude_interaction_generator import ClaudeInteractionGenerator
    from src.lms.analogy_store import save_claude_interaction
    try:
        claude_gen = ClaudeInteractionGenerator()
        claude_result = await claude_gen.generate(
            concept=concept,
            analogy=analogy,
            topic_name=topic.name,
            rag_context=rag_context,
        )
        await save_claude_interaction(
            topic_id=topic_id,
            concept=concept,
            sketch_code=claude_result["sketch_code"],
            steps_json=claude_result["steps"],
            analogy=analogy,
            db_path=_DB_PATH,
        )
    except Exception as e:
        logger.warning("Failed to regenerate Claude interaction: %s", e)

    return {
        "byte": byte_result,
        "sketch_code": sketch_result["sketch_code"],
        "steps": sketch_result["steps"],
    }


@app.get("/api/topic/{topic_id}/concept/{concept}/analogy-suggestions")
async def get_analogy_suggestions(topic_id: str, concept: str):
    """Return 3 alternative analogy suggestions for a concept."""
    from src.lms.analogy_store import get_active_byte
    from src.lms.byte_generator import ByteGenerator
    from src.lms.learning_path import get_topic_by_id

    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get current analogy for context
    byte_row = await get_active_byte(topic_id, concept, db_path=_DB_PATH)
    current_analogy = byte_row.get("analogy", "") if byte_row else ""

    gen = ByteGenerator()
    suggestions = await gen.generate_analogy_suggestions(
        concept=concept,
        topic_name=topic.name,
        current_analogy=current_analogy,
    )
    return {"suggestions": suggestions}


@app.get("/api/topic/{topic_id}/concept/{concept}/notebook")
async def download_notebook(topic_id: str, concept: str):
    """Find best matching .ipynb or generate a fresh notebook; returns as file download."""
    import io
    import nbformat
    from pathlib import Path
    from src.lms.analogy_store import get_p5_sketch
    from src.lms.learning_path import get_topic_by_id

    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    concept_lower = concept.lower()

    # Search for matching .ipynb in data/
    data_dir = Path(__file__).parent / "data"
    best_nb_path: Path | None = None
    best_score = 0

    for nb_path in data_dir.rglob("*.ipynb"):
        try:
            nb_text = nb_path.read_text(errors="ignore")
            score = nb_text.lower().count(concept_lower)
            if score > best_score:
                best_score = score
                best_nb_path = nb_path
        except Exception:
            continue

    if best_nb_path and best_score >= 2:
        logger.info("download_notebook: returning matched notebook %s (score=%d)", best_nb_path, best_score)
        safe_name = concept_lower.replace(" ", "_")[:40] + ".ipynb"
        return FileResponse(
            path=str(best_nb_path),
            filename=safe_name,
            media_type="application/octet-stream",
        )

    # Generate a fresh notebook from p5 step metadata
    sketch_row = await get_p5_sketch(topic_id, concept, db_path=_DB_PATH)
    steps = sketch_row.get("steps", []) if sketch_row else []

    nb = nbformat.v4.new_notebook()
    cells = []

    # Title cell
    cells.append(nbformat.v4.new_markdown_cell(
        f"# {concept}\n\n**Topic:** {topic.name}\n\n"
        f"*Generated by Zizi Byte — AI micro-learning platform*\n\n---"
    ))

    # Install cell
    cells.append(nbformat.v4.new_code_cell(
        "# Install dependencies\n"
        "# !pip install openai langchain qdrant-client\n"
        "import os\n"
        f"# Notebook: {concept}"
    ))

    if steps:
        for step in steps:
            step_idx = step.get("step_index", 0)
            title = step.get("title", f"Step {step_idx + 1}")
            description = step.get("description", "")
            code = step.get("code_snippet", "")
            explanation = step.get("explanation", "")
            language = step.get("language", "python")

            cells.append(nbformat.v4.new_markdown_cell(
                f"## Step {step_idx + 1}: {title}\n\n{description}"
            ))
            if explanation:
                cells.append(nbformat.v4.new_markdown_cell(f"**Explanation:** {explanation}"))
            if code:
                cells.append(nbformat.v4.new_code_cell(code))
    else:
        cells.append(nbformat.v4.new_markdown_cell(
            f"## {concept}\n\nThis notebook covers the concept of {concept} from the topic '{topic.name}'."
        ))
        cells.append(nbformat.v4.new_code_cell(
            f"# Example for {concept}\n"
            "# See course materials for full implementation details\n"
            f"print('Exploring: {concept}')"
        ))

    nb.cells = cells
    nb_str = nbformat.writes(nb)

    safe_name = concept_lower.replace(" ", "_")[:40] + ".ipynb"
    return StreamingResponse(
        io.BytesIO(nb_str.encode("utf-8")),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.get("/api/topic/{topic_id}/concept/{concept}/claude-interaction")
async def get_claude_interaction_endpoint(topic_id: str, concept: str):
    """Return the cached Claude interaction HTML or generate a new one."""
    from src.lms.analogy_store import get_active_byte, get_claude_interaction, save_claude_interaction
    from src.lms.learning_path import get_topic_by_id
    from src.lms.claude_interaction_generator import ClaudeInteractionGenerator
    from src.retrieval.dense_retriever import DenseRetriever

    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Check cache
    cached = await get_claude_interaction(topic_id, concept, db_path=_DB_PATH)
    if cached:
        logger.info("get_claude_interaction: cache HIT topic=%s concept=%s", topic_id, concept)
        return {"sketch_code": cached["sketch_code"], "steps": cached["steps"]}

    # Get analogy from byte cache for context
    byte_row = await get_active_byte(topic_id, concept, db_path=_DB_PATH)
    analogy = byte_row.get("analogy", "") if byte_row else ""

    # Retrieve RAG context
    try:
        retriever = DenseRetriever()
        chunks = await retriever.retrieve(f"{topic.name}: {concept}", k=8)
        rag_context = [
            {
                "content": c.content if hasattr(c, "content") else c["content"],
                "source": c.source if hasattr(c, "source") else c["source"],
            }
            for c in chunks
        ]
    except Exception:
        logger.warning("get_claude_interaction: RAG retrieval failed", exc_info=True)
        rag_context = []

    # Generate
    gen = ClaudeInteractionGenerator()
    result = await gen.generate(
        concept=concept,
        analogy=analogy,
        topic_name=topic.name,
        rag_context=rag_context,
    )

    # Persist
    await save_claude_interaction(
        topic_id=topic_id,
        concept=concept,
        sketch_code=result["sketch_code"],
        steps_json=result["steps"],
        analogy=analogy,
        db_path=_DB_PATH,
    )

    return result


@app.post("/api/topic/{topic_id}/concept/{concept}/render-video")
async def render_video(topic_id: str, concept: str):
    """Stub endpoint for Remotion video render — coming soon."""
    return {"status": "coming_soon", "message": "Video rendering is coming in a future update."}


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "zizi-byte-lms-api"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
