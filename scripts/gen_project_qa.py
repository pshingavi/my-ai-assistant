"""
Generate project-level Q&A for Zizi Byte — covering architecture, design decisions,
tech stack, pipelines, retrieval strategy, agent design, and non-technical overview.

These are the questions an audience/reviewer/interviewer would ask about the project.

Usage:
    uv run python scripts/gen_project_qa.py              # dry-run
    uv run python scripts/gen_project_qa.py --run        # generate all sections
    uv run python scripts/gen_project_qa.py --run --force  # regenerate
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "analogies.db"
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Project sections — each becomes a "topic" in the Q&A explorer
# The context is injected directly (no RAG needed — it's about the project itself)
# ---------------------------------------------------------------------------

PROJECT_SECTIONS = [
    {
        "topic_id": "project-overview",
        "topic_name": "Project Overview & Vision",
        "module_number": "P0",
        "context": """
Zizi Byte is an adaptive AI micro-learning platform built for the AIE9 AI Engineering Certification Challenge.
Tagline: "Learn in bytes. Think in leaps."

The platform transforms dense course materials (PDFs, notebooks, markdown from an 11-module AI Engineering bootcamp)
into personalized, analogy-driven micro-learning experiences called "bytes".

Three modes:
1. LMS (Learn Mode): Byte-sized analogy learning — each concept explained via a creative real-world analogy,
   an interactive animated SVG widget, RAG-grounded deep dive explanation, and share to LinkedIn.
2. Content Pipeline: Automated LinkedIn post generator — research trending AI topics via Tavily+X.com,
   dedup check against previously posted content, RAG-grounded post generation, DALL-E 3 image, post to LinkedIn.
3. Chat: KG+Dense dual retrieval → Cohere Rerank → GPT-4o analogy-first grounded answers.

Tech stack: Python (FastAPI, LangGraph, Chainlit), Next.js 14, Qdrant, SQLite, OpenAI GPT-4o + DALL-E 3,
Anthropic Claude Sonnet 4.6, Cohere Rerank, NetworkX knowledge graph, Tavily search.

The platform is designed for AIE9 cohort students to review and reinforce course material.
""",
    },
    {
        "topic_id": "project-architecture",
        "topic_name": "System Architecture & Design",
        "module_number": "P1",
        "context": """
Zizi Byte architecture:

Entry point: app.py (Chainlit) — keyword-based intent detection routes to LMS link, Content Pipeline, KG view, or Chat.

LMS stack:
- api_server.py (FastAPI, port 8001) — bridges Next.js frontend to Python backend
- zizi-lms/ (Next.js 14, port 3000) — premium light-lavender UI, Framer Motion animations
- ByteGenerator — generates analogy text + why-it-matters + deep dive explanation via GPT-4o
- ClaudeInteractionGenerator — generates animated SVG widget via Claude Sonnet 4.6 with anime.js
- SQLite cache (data/analogies.db) — versioned byte storage, one row per (topic_id, concept, version)

Content Pipeline (LangGraph graph):
- Nodes: research → merge_topics → dedup_check → [conditional] → retrieve_context → generate_post → generate_image → ingest_post
- dedup_check_node is the agentic decision point — cosine similarity vs DEDUP_THRESHOLD

Chat pipeline:
- kg_retrieve → generate_answer
- KGRetriever + DenseRetriever (k=15 each) → deduplicated → Cohere Rerank → top 8 → GPT-4o

Ingestion pipeline (offline, run once):
- CourseIngester handles PDF/notebook/markdown
- Chunks → OpenAI text-embedding-3-small → Qdrant
- Extracts topics/concepts → NetworkX DiGraph (data/topic_graph.json)

Design principles:
- Opt-in integrations: LangSmith tracing (needs LANGCHAIN_API_KEY), X.com search (needs X_BEARER_TOKEN)
- Zero-downtime cache: SQLite versioned rows with is_active flag
- Dual interface: Chainlit for conversational use, Next.js for visual LMS
""",
    },
    {
        "topic_id": "project-retrieval",
        "topic_name": "Retrieval Strategy & Why",
        "module_number": "P2",
        "context": """
Zizi Byte uses three retrieval strategies:

1. DenseRetriever (baseline):
   - Embeds raw user query with text-embedding-3-small
   - Cosine similarity search in Qdrant
   - Used in: ByteGenerator deep dive, Content Pipeline RAG, Q&A generation
   - Why: simple, fast, reliable for direct concept lookup

2. HyDERetriever (Hyde — Hypothetical Document Embeddings):
   - Generates a hypothetical answer document using GPT-4o, then embeds that
   - Better for questions where query phrasing differs from document phrasing
   - Used in: RAGAS evaluation (Task 6 AIE9 Session 10)
   - Why: Closes the query-document semantic gap

3. KGRetriever (Knowledge Graph + Dense):
   - Traverses NetworkX DiGraph to find related topics
   - Runs Dense retrieval on EACH related topic as a sub-query
   - Deduplicates all results, feeds to Cohere Rerank
   - Used in: Chat pipeline, Q&A generation
   - Why: Captures cross-topic relationships that pure dense retrieval misses

Reranking: Cohere Rerank applied after KG+Dense merge in chat — collapses k=30 → top 8 before GPT-4o.

All retrievers implement the same Retriever protocol (base.py) — swappable.

Qdrant collection: course_knowledge_base — auto-created on first upsert.
""",
    },
    {
        "topic_id": "project-agents",
        "topic_name": "Agent Architecture & LangGraph",
        "module_number": "P3",
        "context": """
Zizi Byte uses two LangGraph-based agent pipelines:

1. Content Pipeline (src/agents/content_pipeline.py):
   Architecture: Multi-agent pipeline (not deep agent — each node has a single focused job)
   Graph: research → merge_topics → dedup_check → [branch] → retrieve_context / inform_duplicate → generate_post → generate_image → ingest_post

   Key agentic decision: dedup_check_node computes cosine similarity between new topic embedding
   and all existing post embeddings in Qdrant. If similarity > DEDUP_THRESHOLD, routes to
   inform_duplicate branch instead of generating. This is the autonomous decision-making node.

   Tools used: Tavily (web search), X.com/tweepy (Twitter search), DALL-E 3 (image generation),
   OpenAI GPT-4o (post generation), Qdrant (vector storage).

2. Chat Pipeline (src/agents/chat_pipeline.py):
   Architecture: Linear pipeline — not multi-agent, optimized for latency
   Graph: kg_retrieve → generate_answer

   kg_retrieve: parallel KG traversal + dense retrieval → Cohere Rerank → top 8 chunks
   generate_answer: GPT-4o with analogy-first system prompt, streaming output

Why LangGraph vs plain function calls?
- Explicit state machine makes the flow auditable and traceable via LangSmith
- Conditional edges (dedup branch) are cleaner than nested if/else
- Easy to extend nodes independently without touching other nodes

Agent type classification:
- Content Pipeline: Multi-step tool-using pipeline agent (not deep/recursive)
- Chat: Single-turn RAG agent with retrieval augmentation
- NOT deep agents (no recursive self-improvement loop, no open-ended planning)
""",
    },
    {
        "topic_id": "project-lms-design",
        "topic_name": "LMS Design & Byte Generation",
        "module_number": "P4",
        "context": """
LMS byte generation pipeline (per concept request):

1. Cache check — SQLite lookup for active analogy (topic_id, concept)
2. Analogy generation — GPT-4o generates: analogy text, why-it-matters, deep dive explanation
   with RAG context from DenseRetriever (concept + topic name as query)
3. Image generation — DALL-E 3 generates a scene illustration matching the analogy
   Image stored at zizi-lms/public/generated/images/ — served as Next.js static files
4. Interactive widget — Claude Sonnet 4.6 generates an animated SVG with 5 steps, anime.js
   transitions. Runs in sandboxed iframe (sandbox="allow-scripts" srcdoc).
5. Persist — saved to SQLite with version number, marked is_active=1

Each byte covers ONE concept with 4 tabs:
- Hero section: teaser (first sentence of analogy)
- Analogy tab: full analogy + why it matters
- Interactive tab: animated SVG widget (iframe sandboxed)
- Deep Dive tab: RAG-grounded technical explanation + source citations

Regenerate flow: 3 alternative analogies fetched, user can pick or write custom,
POST /api/topic/{id}/concept/{c}/p5sketch/regenerate clears cache + regenerates all.

Share flow: LinkedIn post generated from byte analogy + ZiziByte attribution,
editable textarea, direct "Post to LinkedIn" opens native LinkedIn composer pre-filled.
Download notebook: .ipynb generated with concept code examples.

Why SQLite? Versioned cache — old bytes preserved, easy rollback, no infra overhead.
Why iframe sandbox? Claude-generated code runs in isolation — XSS protection.
""",
    },
    {
        "topic_id": "project-tech-choices",
        "topic_name": "Technology Choices & Tradeoffs",
        "module_number": "P5",
        "context": """
Key technology decisions in Zizi Byte:

Qdrant (vector database):
- Chosen over Pinecone/Weaviate: self-hosted via Docker, no API key cost, full control
- Supports filtered search, payload storage — concepts stored as payload for KG cross-reference
- Tradeoff: requires Docker dependency, manual ops

NetworkX (knowledge graph):
- In-memory DiGraph, persisted as JSON — lightweight, no graph DB infra
- Supports topic-to-concept edges, concept-to-concept relationships
- Tradeoff: doesn't scale beyond ~10K nodes, no query language
- Why not Neo4j: overkill for 16 topics, 100 concepts

OpenAI GPT-4o:
- Main generation model for analogies, deep dives, posts, answers
- Why: best quality for creative analogy generation, strong structured output

Anthropic Claude Sonnet 4.6:
- Used specifically for SVG/animation generation
- Why: superior code generation for complex anime.js animations vs GPT-4o
- Also used for analogy evaluation in bulk regen scripts

Cohere Rerank:
- Applied after KG+Dense dual retrieval (k=30 total chunks → top 8)
- Why: cross-encoder reranking outperforms cosine similarity for relevance scoring
- Tradeoff: extra API call latency (~200ms)

LangGraph vs plain Python:
- Chosen for auditability via LangSmith tracing
- Conditional branching (dedup check) is cleaner as graph edge
- Cost: slight overhead vs plain async functions

Chainlit vs FastAPI chat:
- Chainlit provides streaming UI, session management out of the box
- No custom WebSocket code needed
- Tradeoff: less control over UI styling

Next.js 14 (App Router) vs React SPA:
- Server components for data fetching (QA page, topic list)
- Static file serving for generated images
- Tradeoff: more complex than CRA, but better performance and SEO
""",
    },
    {
        "topic_id": "project-evals",
        "topic_name": "Evaluation & RAGAS",
        "module_number": "P6",
        "context": """
Zizi Byte evaluation pipeline using RAGAS (RAG Assessment):

Pipeline:
1. Synthetic data generation (evals/synthetic_data_gen.py):
   - Generates question/answer pairs from course chunks using GPT-4o
   - Uses SingleTurnSample format (AIE9 Session 10 API, RAGAS 0.2.x)
   - Default 15 samples, stored as JSON

2. Baseline evaluation (evals/ragas_baseline.py):
   - DenseRetriever: embeds raw query
   - Metrics: answer_relevancy, faithfulness, context_precision, context_recall
   - --delay flag prevents OpenAI rate limiting

3. HyDE evaluation (evals/ragas_hyde.py):
   - HyDERetriever: generates hypothetical document first, then embeds
   - Same metrics as baseline for direct comparison
   - Expected improvement: context_precision (better semantic match)

RAGAS metrics explained:
- answer_relevancy: does the answer address the question?
- faithfulness: is the answer grounded in the retrieved context (no hallucination)?
- context_precision: are the retrieved chunks actually useful for answering?
- context_recall: did we retrieve all the chunks needed to answer?

HyDE hypothesis: For questions like "how does X work?" the hypothetical answer
"X works by..." embeds closer to the actual course explanation than the question itself.
This improves context_precision.

LangSmith tracing: opt-in via LANGCHAIN_API_KEY — traces full generation pipeline.
Each eval run tagged with session name for comparison across runs.
""",
    },
    {
        "topic_id": "project-nontechnical",
        "topic_name": "Non-Technical Overview & Impact",
        "module_number": "P7",
        "context": """
What is Zizi Byte solving?
The problem: AI Engineering course materials are dense, technical, and hard to internalize quickly.
Students struggle to recall concepts, apply them, and articulate them to others.

The solution: Transform dense material into "bytes" — each concept gets:
- A memorable real-world analogy (e.g. "Attention in transformers is like a librarian who reads every book to answer your question")
- An animated visual that makes the concept stick
- A grounded technical explanation for when you need depth
- A LinkedIn post to reinforce by explaining to others (Feynman technique)

The audience: AIE9 cohort students, AI engineers reviewing foundational concepts,
interviewers testing candidates on RAG/agents/retrieval.

Business value:
- Reduces study time: concepts explained in < 2 minutes
- Increases retention: analogy + visual + explanation triple-encodes memory
- Social proof: LinkedIn posts demonstrate learning publicly
- Interview prep: Q&A Explorer for exam-style questions

What makes it different from other learning tools?
- Analogy-first: not definitions, but mental models
- Grounded in real course material via RAG — not hallucinated summaries
- Multi-modal: text + animated visual + notebook download
- Self-improving: content pipeline creates fresh AI content automatically

Scale: 16 course topics × ~6 concepts each = ~96 bytes covering the full AIE9 curriculum.
Build time: built in ~2 weeks as an AIE9 Certification Challenge submission.
""",
    },
]

_SYSTEM_PROMPT = """\
You are a technical educator and AI engineer creating Q&A pairs for a project presentation.

Given a section of project documentation about "Zizi Byte" (an AI micro-learning platform),
generate exactly 8 Q&A pairs covering the questions an audience, reviewer, or interviewer would ask.

RULES:
1. Mix technical and non-technical questions appropriate to the section topic
2. Questions should cover: how it works, why this approach, tradeoffs, alternatives considered,
   real-world impact, edge cases, implementation details
3. Each answer: 2-4 sentences, specific and factual based on the provided context
4. NO fluff — direct, confident answers as the project author would give
5. Return a JSON object with key "qa_pairs":
{"qa_pairs": [{"question": "...", "answer": "...", "sources": ["Zizi Byte Project"]}, ...]}
"""


def get_existing_project_topics(db_path: Path) -> set[str]:
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT topic_id FROM topic_qa WHERE topic_id LIKE 'project-%'"
        ).fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


async def generate_project_qa(section: dict) -> list[dict]:
    from src.llm import get_async_openai
    client = get_async_openai()

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Section: {section['topic_name']}\n\n"
                f"## Project documentation:\n{section['context'].strip()}"
            )},
        ],
        max_tokens=2000,
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    raw = (resp.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            if "qa_pairs" in parsed and isinstance(parsed["qa_pairs"], list):
                parsed = parsed["qa_pairs"]
            elif "question" in parsed and "answer" in parsed:
                parsed = [parsed]
            else:
                for v in parsed.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        parsed = v
                        break
        if not isinstance(parsed, list):
            logger.warning("Unexpected shape for %s: %.200s", section["topic_name"], raw)
            return []
        return [p for p in parsed if isinstance(p, dict) and p.get("question") and p.get("answer")]
    except Exception as e:
        logger.warning("Parse failed for %s: %s", section["topic_name"], e)
        return []


async def main(dry_run: bool, force: bool) -> None:
    from src.lms.analogy_store import init_db, save_qa_pairs

    await init_db(str(DB_PATH))
    existing = get_existing_project_topics(DB_PATH) if not force else set()
    pending = [s for s in PROJECT_SECTIONS if force or s["topic_id"] not in existing]
    skipped = len(PROJECT_SECTIONS) - len(pending)

    logger.info(
        "Project sections: %d total, %d to generate, %d already exist",
        len(PROJECT_SECTIONS), len(pending), skipped,
    )

    if dry_run:
        for s in pending:
            logger.info("  [%s] %s", s["module_number"], s["topic_name"])
        logger.info("DRY RUN — re-run with --run to generate.")
        return

    for i, section in enumerate(pending, 1):
        logger.info("[%d/%d] %s — '%s'", i, len(pending), section["module_number"], section["topic_name"])
        try:
            pairs = await generate_project_qa(section)
        except Exception as e:
            logger.error("Failed for %s: %s", section["topic_name"], e)
            continue

        if not pairs:
            logger.warning("  No Q&A generated for %s — skipping", section["topic_name"])
            continue

        await save_qa_pairs(str(DB_PATH), section["topic_id"], section["topic_name"], section["module_number"], pairs)
        logger.info("  ✓ Saved %d Q&A pairs for '%s'", len(pairs), section["topic_name"])
        await asyncio.sleep(0.3)

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate project Q&A for Zizi Byte.")
    parser.add_argument("--run", action="store_true", help="Apply (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if Q&A already exists")
    args = parser.parse_args()
    asyncio.run(main(dry_run=not args.run, force=args.force))
