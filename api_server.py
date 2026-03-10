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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Zizi Byte LMS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    """Generate a byte-sized analogy-first learning card for one concept."""
    from src.lms.learning_path import get_topic_by_id
    from src.lms.byte_generator import ByteGenerator

    topic = get_topic_by_id(req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    gen = ByteGenerator()
    byte_content = await gen.generate_byte(topic.name, req.concept)
    return asdict(byte_content)


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
        "selected_topic": topic.name,
        "topic_description": topic.description,
        "is_duplicate": False,
        "duplicate_reason": "",
        "kb_context": [],
        "linkedin_post": "",
        "image_url": "",
        "image_local_path": "",
        "analogy_summary": "",
        "messages": [],
        "error": "",
    }

    state.update(await dedup_check_node(state))
    if state["is_duplicate"]:
        return {"is_duplicate": True, "reason": state["duplicate_reason"]}

    state.update(await retrieve_context_node(state))
    state.update(await generate_post_node(state))
    state.update(await generate_image_node(state))
    await ingest_post_node(state)

    return {
        "is_duplicate": False,
        "topic": topic.name,
        "post": state["linkedin_post"],
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


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "zizi-byte-lms-api"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
