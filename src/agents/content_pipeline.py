"""Content Creation Pipeline — LangGraph graph.

Flow:
  research → merge_topics → dedup_check
    → [duplicate?] inform → END
    → [new topic]  retrieve_context → generate_post → generate_image → ingest → END

The agentic decision point is dedup_check_node: it decides at runtime whether
to continue the pipeline or stop and inform the user of an already-covered topic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.state import ContentState
from src.config import get_settings
from src.ingestion.post_ingester import GeneratedPost, PostIngester
from src.llm import embed_texts, get_async_openai
from src.memory.qdrant_store import search
from src.retrieval.dense_retriever import DenseRetriever
from src.tools.image_tool import generate_poster
from src.tools.tavily_tool import TopicResult, search_trending_topics
from src.tools.x_tool import search_x_topics

logger = logging.getLogger(__name__)

_LINKEDIN_SYSTEM = """You are an expert LinkedIn content creator specializing in AI/technology.
Your posts consistently go viral because you use a specific structure:

## POST STRUCTURE (follow exactly):

**HOOK (lines 1-2)**
- A bold, attention-grabbing statement that challenges assumptions or reveals a surprising truth
- Must be self-contained — the reader decides to keep reading based on these 2 lines alone
- No "I'm excited to share", "Just learned", or weak openers
- Good examples:
  • "Most developers debug their RAG by adding more data. That's the wrong fix."
  • "Your vector database isn't the bottleneck. Your chunking strategy is."

**ANALOGY STORY (3-5 short paragraphs)**
- Open with a vivid, specific scene — a chef, a detective, a jazz musician, a librarian
- The metaphor must create an "aha!" moment for non-technical readers
- Be specific: name the chef's dish, describe the detective's case
- Bridge back to the tech concept naturally in the last sentence
- Use 1 relevant emoji for visual anchor

**TECH CONCEPT (4-6 short paragraphs)**
- Explain the actual technology accurately and clearly
- Reference real technical specifics (show you did your homework)
- One idea per paragraph, short sentences
- Include numbers/benchmarks where available from the context
- Cite source material when relevant

**CALL TO ACTION (2 lines)**
- Ask a discussion-provoking question OR invite reshares
- End with 4-5 relevant hashtags

**FORMATTING RULES**
- Total length: 800-1200 characters
- Short paragraphs (1-3 lines), blank line between each
- No bullet points or headers in the post itself
- Hashtags on the last line only"""

_TOPIC_MERGE_PROMPT = """You are given trending topics from Tavily web search and X.com.
Your job: identify the single HOTTEST, most specific topic for a LinkedIn post about {domain}.

Strict selection criteria — pick the topic that scores highest on ALL of these:
1. RECENCY — is it from this week/month? A fresh paper, model release, or product launch beats stale news.
2. SPECIFICITY — "GPT-4o vision capabilities for code review" beats "AI is improving". Be precise.
3. Technical depth — real engineering content AI engineers can learn from.
4. Analogy potential — can the core idea be explained with a vivid, unexpected metaphor?
5. Surprise factor — would an AI engineer stop scrolling? Does it challenge a common assumption?

DO NOT pick generic topics like "AI is advancing" or "LLMs are improving".
DO pick specific: a named model, a named technique, a named benchmark result, a specific paper finding.

Topics:
{topics_json}

Return ONLY valid JSON:
{{
  "topic": "Specific topic name — include model/paper/technique name (4-10 words)",
  "description": "2-3 sentences: what exactly happened, why it matters technically, what the key insight is",
  "analogy_idea": "One vivid, specific analogy sentence — name the scene (e.g. 'Like a chef who...')"
}}"""


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def research_node(state: ContentState) -> dict:
    """Fetch trending topics from Tavily and X.com in parallel."""
    import asyncio
    domain = state.get("domain") or get_settings().content_domain
    tavily, x = await asyncio.gather(
        search_trending_topics(domain),
        search_x_topics(domain),
    )
    logger.info("Research: %d Tavily + %d X topics", len(tavily), len(x))
    return {"tavily_topics": tavily, "x_topics": x}


async def merge_topics_node(state: ContentState) -> dict:
    """LLM selects the best single topic from merged Tavily + X results."""
    cfg = get_settings()
    client = get_async_openai()
    domain = state.get("domain") or cfg.content_domain

    all_topics = [
        {"source": t.source, "title": t.title, "description": t.description}
        for t in (state.get("tavily_topics") or []) + (state.get("x_topics") or [])
    ]
    if not all_topics:
        return {"selected_topic": "AI Agent Architecture", "topic_description": "Overview of agentic AI systems"}

    prompt = _TOPIC_MERGE_PROMPT.format(
        domain=domain, topics_json=json.dumps(all_topics[:15], indent=2)
    )
    response = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(response.choices[0].message.content or "{}")
        topic = data.get("topic", all_topics[0]["title"])
        description = data.get("description", "")
        analogy_summary = data.get("analogy_idea", "")
        logger.info("Selected topic: '%s'", topic)
        return {
            "selected_topic": topic,
            "topic_description": description,
            "analogy_summary": analogy_summary,
        }
    except json.JSONDecodeError:
        return {
            "selected_topic": all_topics[0]["title"],
            "topic_description": all_topics[0].get("description", ""),
            "analogy_summary": "",
        }


async def dedup_check_node(state: ContentState) -> dict:
    """THE AGENTIC DECISION POINT: check if topic was already posted about.

    Embeds the selected topic and checks the posts_collection for similar posts.
    If similarity > dedup_threshold → mark as duplicate so the graph branches.
    """
    cfg = get_settings()
    topic = state.get("selected_topic", "")
    if not topic:
        return {"is_duplicate": False, "duplicate_reason": ""}

    try:
        from src.memory.qdrant_store import ensure_collection
        ensure_collection(cfg.posts_collection)
        vectors = await embed_texts([topic])
        results = search(
            collection_name=cfg.posts_collection,
            query_vector=vectors[0],
            k=1,
        )
        if results and results[0].score >= cfg.dedup_threshold:
            reason = f"Similar topic '{results[0].source}' was already covered (similarity={results[0].score:.2f})"
            logger.info("Dedup: DUPLICATE — %s", reason)
            return {"is_duplicate": True, "duplicate_reason": reason}
    except Exception:
        logger.warning("Dedup check failed — treating as new topic", exc_info=True)

    return {"is_duplicate": False, "duplicate_reason": ""}


def should_continue(state: ContentState) -> str:
    """Conditional edge: duplicate → stop, new → continue pipeline."""
    return "duplicate" if state.get("is_duplicate") else "continue"


async def inform_duplicate_node(state: ContentState) -> dict:
    """Inform user this topic was already covered; suggest alternatives."""
    topic = state.get("selected_topic", "this topic")
    reason = state.get("duplicate_reason", "")
    msg = (
        f"⚠️ **Topic already covered**: {topic}\n\n"
        f"{reason}\n\n"
        "Try asking me to search again — I'll find a fresh angle."
    )
    return {"messages": [AIMessage(content=msg)]}


async def retrieve_context_node(state: ContentState) -> dict:
    """Retrieve relevant AIE9 course material for the selected topic via Dense retrieval."""
    topic = state.get("selected_topic", "")
    description = state.get("topic_description", "")
    query = f"{topic}: {description}"

    retriever = DenseRetriever()
    chunks = await retriever.retrieve(query, k=get_settings().default_k)
    kb_context = [
        {"content": c.content, "score": c.score, "source": c.source}
        for c in chunks
    ]
    logger.info("Retrieved %d KB chunks for topic '%s'", len(chunks), topic)
    return {"kb_context": kb_context}


async def generate_post_node(state: ContentState) -> dict:
    """Generate the Hook → Analogy → Tech Concept → CTA LinkedIn post."""
    cfg = get_settings()
    client = get_async_openai()
    topic = state.get("selected_topic", "")
    description = state.get("topic_description", "")
    analogy_hint = state.get("analogy_summary", "")
    kb_context = state.get("kb_context", [])

    context_str = "\n\n".join(
        f"[Source: {c['source']}, score={c['score']:.2f}]\n{c['content']}"
        for c in kb_context[:5]
    )

    analogy_section = (
        f"Use this exact analogy from the ZiziByte learning byte for the analogy story section:\n"
        f"\"{analogy_hint}\"\n"
        "Build the analogy story directly around this — do not invent a different one.\n\n"
        if analogy_hint
        else f"Analogy idea to explore: {analogy_hint}\n\n"
    )

    user_prompt = (
        f"Write a LinkedIn post about: **{topic}**\n\n"
        f"Topic context: {description}\n\n"
        f"{analogy_section}"
        f"Knowledge base context to ground the tech section:\n{context_str}\n\n"
        "Follow the structure in your instructions exactly. "
        "Make the hook genuinely surprising. Make the analogy vivid and specific.\n\n"
        "End the post with this line verbatim as the last line:\n"
        "🧠 Concept explained by #ZiziByte — Learn in bytes. Think in leaps. 🚀"
    )

    response = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": _LINKEDIN_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        temperature=0.8,
    )
    post = response.choices[0].message.content or ""
    logger.info("Generated LinkedIn post (%d chars) for topic '%s'", len(post), topic)
    return {
        "linkedin_post": post,
        "messages": [AIMessage(content=post)],
    }


async def generate_image_node(state: ContentState) -> dict:
    """Generate a DALL-E 3 poster image for the post."""
    topic = state.get("selected_topic", "")
    analogy = state.get("analogy_summary", topic)

    url, local_path = await generate_poster(topic, analogy)
    return {
        "image_url": url,
        "image_local_path": str(local_path) if local_path else "",
    }


async def ingest_post_node(state: ContentState) -> dict:
    """Store the generated post + topic to Qdrant and update the KG."""
    # Collect all media URLs from X.com source topics
    source_media: list[str] = []
    for t in (state.get("x_topics") or []):
        source_media.extend(getattr(t, "media_urls", []) or [])

    post = GeneratedPost(
        topic=state.get("selected_topic", ""),
        post_text=state.get("linkedin_post", ""),
        image_url=state.get("image_url", ""),
        image_path=state.get("image_local_path", ""),
        analogy_summary=state.get("analogy_summary", ""),
        source_media_urls=source_media or None,
    )
    ingester = PostIngester()
    n = await ingester.ingest(post)
    logger.info("Ingested post to Qdrant (%d chunks) + KG", n)
    return {}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_content_graph() -> CompiledStateGraph:
    builder = StateGraph(ContentState)

    builder.add_node("research", research_node)
    builder.add_node("merge_topics", merge_topics_node)
    builder.add_node("dedup_check", dedup_check_node)
    builder.add_node("inform_duplicate", inform_duplicate_node)
    builder.add_node("retrieve_context", retrieve_context_node)
    builder.add_node("generate_post", generate_post_node)
    builder.add_node("generate_image", generate_image_node)
    builder.add_node("ingest_post", ingest_post_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "merge_topics")
    builder.add_edge("merge_topics", "dedup_check")
    builder.add_conditional_edges(
        "dedup_check",
        should_continue,
        {"duplicate": "inform_duplicate", "continue": "retrieve_context"},
    )
    builder.add_edge("inform_duplicate", END)
    builder.add_edge("retrieve_context", "generate_post")
    builder.add_edge("generate_post", "generate_image")
    builder.add_edge("generate_image", "ingest_post")
    builder.add_edge("ingest_post", END)

    return builder.compile()
