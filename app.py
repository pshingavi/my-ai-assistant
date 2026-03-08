"""Chainlit application — AI Content Creator.

Two modes, detected from the user's message:
  • CONTENT mode  — triggered by keywords like "create", "write post", "find topics"
  • CHAT mode     — everything else → Knowledge Graph RAG Q&A

Pipeline progress is shown as Chainlit Steps (accordion UI).
"""

from __future__ import annotations

import logging

import chainlit as cl

from src.agents.chat_pipeline import build_chat_graph
from src.agents.content_pipeline import build_content_graph
from src.config import get_settings
from src.memory.qdrant_store import ensure_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_CREATE_KEYWORDS = {
    "create", "write post", "write a post", "find topics", "trending",
    "generate post", "new post", "linkedin post", "content",
}

_KG_KEYWORDS = {
    "kg", "knowledge graph", "graph", "topic graph", "learning path",
    "show topics", "what topics", "course topics", "topic map",
}

_LMS_KEYWORDS = {
    "learn", "lms", "study", "byte", "lesson", "course", "module",
    "interactive", "learning mode",
}

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start() -> None:
    cfg = get_settings()
    cfg.configure_langsmith()

    # Ensure Qdrant collections exist
    try:
        ensure_collection(cfg.kb_collection)
        ensure_collection(cfg.posts_collection)
    except Exception:
        logger.warning("Could not connect to Qdrant — is Docker running?")

    # Build graphs once per session
    cl.user_session.set("content_graph", build_content_graph())
    cl.user_session.set("chat_graph", build_chat_graph())
    cl.user_session.set("domain", cfg.content_domain)

    await cl.Message(
        content=(
            f"👋 Welcome to **{cfg.app_name}**!\n\n"
            f"I help you create viral LinkedIn posts about **{cfg.content_domain}** "
            "and answer your questions about AI/ML concepts.\n\n"
            "**Try:**\n"
            "- `create` — find trending topics and generate a post\n"
            "- `kg` — view the GenAI knowledge graph\n"
            "- `What is the agent loop?` — chat with the knowledge base\n"
            "- `Explain RAG like I'm a chef` — analogy-driven explanation"
        )
    ).send()


# ── Message handler ───────────────────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = message.content.strip().lower()
    is_create_mode = any(kw in text for kw in _CREATE_KEYWORDS)

    is_kg_mode = any(kw in text for kw in _KG_KEYWORDS)

    is_lms_mode = any(kw in text for kw in _LMS_KEYWORDS) and not is_create_mode

    if is_create_mode:
        await _run_content_pipeline(message.content)
    elif is_kg_mode:
        await _show_knowledge_graph()
    elif is_lms_mode:
        await cl.Message(
            content=(
                "## 🎓 Zizi Byte LMS\n\n"
                "The interactive byte-sized learning experience is available at:\n\n"
                "**[http://localhost:3000](http://localhost:3000)**\n\n"
                "Start the LMS frontend with:\n"
                "```bash\ncd zizi-lms && npm run dev\n```\n"
                "And the API server with:\n"
                "```bash\nuv run python api_server.py\n```\n\n"
                "Or ask me anything here — I'll answer with analogy-first grounded explanations."
            )
        ).send()
    else:
        await _run_chat_pipeline(message.content)


# ── Knowledge Graph View ──────────────────────────────────────────────────────

async def _show_knowledge_graph() -> None:
    from src.tools.kg_viz_tool import build_kg_figure

    async with cl.Step(name="🧠 Building Knowledge Graph", type="tool") as step:
        fig = build_kg_figure()
        from src.memory.topic_graph import get_topic_graph
        kg = get_topic_graph()
        stats = kg.stats()
        step.output = f"{stats['nodes']} topics, {stats['edges']} connections"

    if fig is None:
        await cl.Message(
            content=(
                "The knowledge graph is empty.\n\n"
                "Run `uv run python scripts/ingest_courses.py` to populate course topics, "
                "then type `create` to add generated post topics."
            )
        ).send()
        return

    await cl.Message(
        content=(
            "## GenAI Knowledge Graph\n\n"
            "Purple nodes = bootcamp course topics | Blue diamonds = generated posts\n"
            "Hover over any node to see its description and concepts."
        ),
        elements=[cl.Plotly(figure=fig, display="inline", size="large")],
    ).send()


# ── Content Pipeline ──────────────────────────────────────────────────────────

async def _run_content_pipeline(user_request: str) -> None:
    graph = cl.user_session.get("content_graph")
    domain = cl.user_session.get("domain") or get_settings().content_domain

    # ── Step 1: Research ──────────────────────────────────────────────────────
    async with cl.Step(name="🔍 Research — Tavily + X.com", type="tool") as step:
        state = {
            "domain": domain,
            "user_request": user_request,
            "tavily_topics": [],
            "x_topics": [],
            "selected_topic": "",
            "topic_description": "",
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
        # Run research + merge nodes only
        from src.agents.content_pipeline import research_node, merge_topics_node
        state.update(await research_node(state))
        state.update(await merge_topics_node(state))
        step.output = f"Selected topic: **{state['selected_topic']}**\n{state['topic_description']}"

    # Show X.com media from the research results
    x_media_elements: list[cl.Image] = []
    for t in (state.get("x_topics") or []):
        for murl in (t.media_urls or []):
            if murl:
                x_media_elements.append(cl.Image(url=murl, name=t.title[:60], display="inline"))
    if x_media_elements:
        await cl.Message(
            content="📸 **X.com media from trending posts**",
            elements=x_media_elements[:6],
        ).send()

    # ── Step 2: Dedup ─────────────────────────────────────────────────────────
    async with cl.Step(name="🔄 Dedup Check", type="tool") as step:
        from src.agents.content_pipeline import dedup_check_node
        state.update(await dedup_check_node(state))
        if state["is_duplicate"]:
            step.output = f"⚠️ Duplicate: {state['duplicate_reason']}"
            await cl.Message(content=state["duplicate_reason"]).send()
            return
        step.output = "✅ New topic — proceeding"

    # ── Step 3: RAG Context ───────────────────────────────────────────────────
    async with cl.Step(name="📚 Retrieving Course Context (Dense)", type="tool") as step:
        from src.agents.content_pipeline import retrieve_context_node
        state.update(await retrieve_context_node(state))
        sources = list({c["source"] for c in state["kb_context"]})
        step.output = f"Retrieved {len(state['kb_context'])} chunks from: {', '.join(sources[:5])}"

    # ── Step 4: Generate Post ─────────────────────────────────────────────────
    async with cl.Step(name="✍️ Generating LinkedIn Post", type="llm") as step:
        from src.agents.content_pipeline import generate_post_node
        state.update(await generate_post_node(state))
        step.output = f"Post generated ({len(state['linkedin_post'])} chars)"

    # Display the post prominently
    await cl.Message(
        content=f"## 📝 LinkedIn Post — {state['selected_topic']}\n\n{state['linkedin_post']}"
    ).send()

    # ── Post sources: Tavily + X.com citations ────────────────────────────────
    post_source_elements: list[cl.Text] = []
    for t in (state.get("tavily_topics") or []):
        if t.url:
            post_source_elements.append(
                cl.Text(
                    name=f"[Tavily] {t.title[:70]}",
                    content=f"{t.description}\n\nURL: {t.url}",
                    display="side",
                )
            )
    for t in (state.get("x_topics") or [])[:5]:
        if t.url:
            post_source_elements.append(
                cl.Text(
                    name=f"[X.com] {t.title[:70]}",
                    content=f"{t.description}\n\nURL: {t.url}",
                    display="side",
                )
            )
    if post_source_elements:
        await cl.Message(content="**Sources used for this post**", elements=post_source_elements).send()

    # ── Step 5: Image ─────────────────────────────────────────────────────────
    async with cl.Step(name="🎨 Generating Poster Image (gpt-image-1)", type="tool") as step:
        from src.agents.content_pipeline import generate_image_node
        state.update(await generate_image_node(state))
        if state["image_url"]:
            step.output = f"Image ready: {state['image_url'][:80]}..."
        else:
            step.output = "Image generation skipped or failed"

    # Show image if generated
    if state.get("image_local_path"):
        try:
            image = cl.Image(
                path=state["image_local_path"],
                name=f"{state['selected_topic']} poster",
                display="inline",
            )
            await cl.Message(content="🖼️ **Poster Image**", elements=[image]).send()
        except Exception:
            if state.get("image_url"):
                await cl.Message(content=f"🖼️ [View poster image]({state['image_url']})").send()

    # ── Step 6: Ingest ────────────────────────────────────────────────────────
    async with cl.Step(name="💾 Saving to Knowledge Base + Graph", type="tool") as step:
        from src.agents.content_pipeline import ingest_post_node
        await ingest_post_node(state)
        step.output = "Post stored in Qdrant + Knowledge Graph updated"

    await cl.Message(
        content=(
            "✅ **Done!** Post saved to your knowledge base.\n\n"
            "You can now chat about this topic — try asking: "
            f"*\"Explain {state['selected_topic']} with an analogy\"*"
        )
    ).send()


# ── Chat Pipeline ─────────────────────────────────────────────────────────────


async def _run_chat_pipeline(query: str) -> None:
    from src.config import get_settings
    cfg = get_settings()

    # ── Step 1: KG + Dense retrieval (large candidate pool for reranking) ────────
    async with cl.Step(name="🧠 Knowledge Graph + Dense Retrieval", type="tool") as step:
        from src.retrieval.kg_retriever import KGRetriever
        from src.retrieval.dense_retriever import DenseRetriever

        _CANDIDATE_K = 15  # large pool so Cohere rerank has full coverage

        # KG retrieval: multi-hop expanded queries
        kg_chunks = await KGRetriever().retrieve(query, k=_CANDIDATE_K)

        # Direct dense on the raw query — ensures the most obvious matches survive
        dense_raw = await DenseRetriever().retrieve(query, k=_CANDIDATE_K)

        # Merge both sets, keep highest cosine score per unique chunk
        combined: dict[str, dict] = {}
        for c in [*kg_chunks, *dense_raw]:
            key = c.content[:100] if hasattr(c, "content") else c["content"][:100]
            entry = {
                "content": c.content if hasattr(c, "content") else c["content"],
                "score": c.score if hasattr(c, "score") else c["score"],
                "source": c.source if hasattr(c, "source") else c["source"],
                "metadata": c.metadata if hasattr(c, "metadata") else c.get("metadata", {}),
            }
            if key not in combined or entry["score"] > combined[key]["score"]:
                combined[key] = entry

        chunks: list[dict] = sorted(combined.values(), key=lambda c: c["score"], reverse=True)[:_CANDIDATE_K]
        max_score = max((c["score"] for c in chunks), default=0.0)
        step.output = f"Retrieved {len(chunks)} candidates (max relevance: {max_score:.2f})"

    # ── Step 2: Cohere Rerank (if available) ──────────────────────────────────
    async with cl.Step(name="🎯 Cohere Rerank", type="tool") as step:
        try:
            from src.retrieval.rerank_retriever import RerankRetriever
            reranker = RerankRetriever()
            if reranker._has_cohere:
                import asyncio, time
                from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
                from langchain_cohere import CohereRerank
                from src.memory.qdrant_store import get_langchain_retriever as _get_lc_retriever

                # Build a temporary in-memory retriever from already-fetched chunks
                from langchain_core.documents import Document
                from langchain_core.retrievers import BaseRetriever
                from langchain_core.callbacks import CallbackManagerForRetrieverRun

                class _MemRetriever(BaseRetriever):
                    docs: list[Document]
                    def _get_relevant_documents(self, q, *, run_manager=None):
                        return self.docs

                mem_docs = [
                    Document(
                        page_content=c["content"],
                        metadata={"source": c["source"], **c.get("metadata", {})}
                    )
                    for c in chunks
                ]
                compressor = CohereRerank(model="rerank-v3.5", top_n=5)
                compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=_MemRetriever(docs=mem_docs),
                )
                reranked_docs = await asyncio.to_thread(compression_retriever.invoke, query)
                if reranked_docs:
                    chunks = [
                        {
                            "content": d.page_content,
                            "score": d.metadata.get("relevance_score", 0.0),
                            "source": d.metadata.get("source", "unknown"),
                            "metadata": d.metadata,
                        }
                        for d in reranked_docs
                    ]
                    step.output = f"Reranked to {len(chunks)} chunks"
                else:
                    step.output = "Rerank returned no results — using KG results"
            else:
                step.output = "Skipped (no COHERE_API_KEY)"
        except Exception as e:
            step.output = f"Skipped ({e})"

    # ── Step 3: Stream answer ─────────────────────────────────────────────────
    context_str = "\n\n---\n\n".join(
        f"[Source: {c['source']}, relevance={c['score']:.2f}]\n{c['content']}"
        for c in chunks[:6]
    )

    _CHAT_SYSTEM = (
        "You are an expert AI engineering educator. Every claim you make MUST be grounded "
        "in the retrieved context below — do NOT use outside knowledge.\n\n"
        "RULES:\n"
        "- Lead with a vivid analogy that makes the concept intuitive.\n"
        "- For each factual claim, cite the source file name in parentheses, "
        "e.g. (AIE9_Session05_MultiAgent.pdf) or (web: venturebeat.com).\n"
        "- If the context has low relevance scores (< 0.4), acknowledge: "
        "'My course material has limited coverage of this — here is what I found:'\n"
        "- Never fabricate facts. If the context doesn't cover the question, say so.\n"
        "- End with one thought-provoking follow-up question.\n\n"
        f"## Retrieved context (CITE THESE):\n{context_str or 'No relevant context found in course KB.'}"
    )

    response_msg = cl.Message(content="")
    await response_msg.send()

    from src.llm import get_async_openai
    client = get_async_openai()
    stream = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": _CHAT_SYSTEM},
            {"role": "user", "content": query},
        ],
        max_tokens=700,
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            await response_msg.stream_token(delta.content)
    await response_msg.update()

    # ── Sources — compact list only ────────────────────────────────────────────
    source_lines: list[str] = []
    seen_sources: set[str] = set()

    for i, c in enumerate(chunks[:6], 1):
        source = c.get("source", "unknown")
        score = c.get("score", 0.0)
        if source not in seen_sources:
            seen_sources.add(source)
            source_lines.append(f"{i}. **{source}** (relevance: {score:.2f})")

    if source_lines:
        sources_md = "**📚 Sources:**\n" + "\n".join(source_lines)
    else:
        sources_md = "⚠️ No course material found for this query."

    await cl.Message(content=sources_md).send()
