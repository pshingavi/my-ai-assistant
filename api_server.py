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
    from src.tools.image_tool import generate_image as _gen_image

    image_prompt = (
        f"Minimalist digital illustration: {req.prompt}. "
        "No text, no labels. Clean background. Educational, friendly style."
    )
    result = await _gen_image(req.topic_name, image_prompt)
    if not result:
        raise HTTPException(status_code=500, detail="Image generation failed")
    return {"image_url": result.get("url", ""), "local_path": result.get("local_path", "")}


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


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "zizi-byte-lms-api"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
