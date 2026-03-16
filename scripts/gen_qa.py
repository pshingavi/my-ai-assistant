"""
Generate Q&A pairs for all course topics using RAG from course material.

Stores results in the topic_qa SQLite table.

Usage:
    uv run python scripts/gen_qa.py              # dry-run: list topics
    uv run python scripts/gen_qa.py --run        # generate all
    uv run python scripts/gen_qa.py --run --topic "RAG Fundamentals"  # single topic
    uv run python scripts/gen_qa.py --run --force  # regenerate even if Q&A exists
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "analogies.db"
sys.path.insert(0, str(ROOT))

_QA_SYSTEM = """\
You are a technical educator creating exam-quality Q&A pairs for an AIE9 AI Engineering bootcamp.

Given a topic and retrieved course material, generate exactly 6 Q&A pairs.

RULES:
1. Questions must be SPECIFIC and TECHNICAL — not "what is X?" but "how does X achieve Y in practice?" or "why does X outperform Y in Z scenario?"
2. Each answer: 2-4 sentences, grounded ONLY in retrieved context, cite source file in parentheses at least once, e.g. (Session04_RAG.pdf)
3. Cover different angles across the 6 pairs: mechanism, tradeoff, implementation detail, comparison, real-world application, limitation
4. Return a JSON object with a single key "qa_pairs" containing an array:
{"qa_pairs": [{"question": "...", "answer": "...", "sources": ["Session04_RAG.pdf"]}, ...]}
"""


def get_existing_topics(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT topic_id FROM topic_qa").fetchall()
        return {r[0] for r in rows}
    except Exception:
        return set()
    finally:
        conn.close()


async def generate_qa_for_topic(topic_id: str, topic_name: str, description: str, concepts: list[str], module_number: str) -> list[dict]:
    from src.retrieval.dense_retriever import DenseRetriever
    from src.retrieval.kg_retriever import KGRetriever
    from src.llm import get_async_openai

    client = get_async_openai()
    query = f"{topic_name}: {', '.join(concepts[:5])}"

    try:
        dense_chunks = await DenseRetriever().retrieve(query, k=8)
        kg_chunks = await KGRetriever().retrieve(query, k=6)
        seen: dict[str, dict] = {}
        for c in [*dense_chunks, *kg_chunks]:
            content = c.content if hasattr(c, "content") else c["content"]
            source = c.source if hasattr(c, "source") else c["source"]
            key = content[:120]
            if key not in seen:
                seen[key] = {"content": content, "source": source}
        chunks = list(seen.values())[:12]
    except Exception as e:
        logger.warning("Retrieval failed for %s: %s", topic_name, e)
        chunks = []

    context_str = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['content']}" for c in chunks
    ) or "No relevant course context found."

    user_msg = (
        f"Topic: {topic_name}\n"
        f"Module: {module_number}\n"
        f"Description: {description}\n"
        f"Key concepts: {', '.join(concepts[:8])}\n\n"
        f"## Retrieved course context:\n{context_str[:4000]}"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _QA_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=1500,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    raw = (resp.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw)
        # Expected: {"qa_pairs": [...]}
        if isinstance(parsed, dict):
            # Try "qa_pairs" key first
            if "qa_pairs" in parsed and isinstance(parsed["qa_pairs"], list):
                parsed = parsed["qa_pairs"]
            # Fallback: single Q&A object {"question": ..., "answer": ...}
            elif "question" in parsed and "answer" in parsed:
                parsed = [parsed]
            else:
                # Find first list of dicts
                for v in parsed.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        parsed = v
                        break
        if not isinstance(parsed, list):
            logger.warning("Unexpected response shape for %s: %.200s", topic_name, raw)
            return []
        return [p for p in parsed if isinstance(p, dict) and p.get("question") and p.get("answer")]
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Parse failed for %s: %s — raw: %.200s", topic_name, e, raw)
        return []


async def main(dry_run: bool, topic_filter: str | None, force: bool) -> None:
    from src.lms.learning_path import get_all_topics
    from src.lms.analogy_store import init_db, save_qa_pairs

    await init_db(str(DB_PATH))

    all_topics = [t for t in get_all_topics() if not t.is_post]
    if topic_filter:
        all_topics = [t for t in all_topics if topic_filter.lower() in t.name.lower()]

    existing = get_existing_topics(DB_PATH) if not force else set()

    pending = [t for t in all_topics if force or t.id not in existing]
    skipped = len(all_topics) - len(pending)

    logger.info("Topics: %d total, %d to generate, %d already have Q&A", len(all_topics), len(pending), skipped)

    if dry_run:
        for t in pending:
            logger.info("  [%s] %s — %d concepts", t.module_number, t.name, len(t.concepts))
        logger.info("DRY RUN — re-run with --run to generate.")
        return

    for i, topic in enumerate(pending, 1):
        logger.info("[%d/%d] %s — '%s'", i, len(pending), topic.module_number, topic.name)
        try:
            pairs = await generate_qa_for_topic(
                topic_id=topic.id,
                topic_name=topic.name,
                description=topic.description,
                concepts=topic.concepts,
                module_number=topic.module_number,
            )
        except Exception as e:
            logger.error("Failed for %s: %s", topic.name, e)
            continue

        if not pairs:
            logger.warning("  No Q&A generated for %s — skipping", topic.name)
            continue

        await save_qa_pairs(str(DB_PATH), topic.id, topic.name, topic.module_number, pairs)
        logger.info("  ✓ Saved %d Q&A pairs for '%s'", len(pairs), topic.name)
        await asyncio.sleep(0.3)

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Q&A pairs for all course topics.")
    parser.add_argument("--run", action="store_true", help="Apply (default: dry-run)")
    parser.add_argument("--topic", type=str, default=None, help="Filter to topics matching this name substring")
    parser.add_argument("--force", action="store_true", help="Regenerate even if Q&A already exists")
    args = parser.parse_args()

    asyncio.run(main(dry_run=not args.run, topic_filter=args.topic, force=args.force))
