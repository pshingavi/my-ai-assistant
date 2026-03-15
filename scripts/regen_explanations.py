"""
Patch empty (or thin) Deep Dive explanations in-place.

Only touches the `explanation` column in the analogies table.
Does NOT regenerate analogy text, images, or Claude interactions.

Usage:
    uv run python scripts/regen_explanations.py              # dry-run: show which rows are empty
    uv run python scripts/regen_explanations.py --run        # patch all empty explanations
    uv run python scripts/regen_explanations.py --run --concept "what is RAG"  # single concept
    uv run python scripts/regen_explanations.py --run --min-length 80  # also patch thin ones (<80 chars)
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

_EXPLANATION_SYSTEM = """\
You are a technical educator grounding AI/ML concept explanations in retrieved course material.

Write a clear technical explanation (100-200 words) for the given concept.

RULES:
1. Ground EVERY claim in the retrieved course context chunks below.
2. Cite the source file in parentheses at least once, e.g. (Session04_RAG.pdf).
3. If the context is thin or off-topic, use what IS there and note the limitation.
4. Be technically precise — this is for AI engineers, not beginners.
5. Do NOT include an analogy — that lives in a separate tab.
6. Return ONLY the explanation text, no JSON, no headers.
"""


def get_empty_rows(db_path: Path, min_length: int, concept_filter: str | None) -> list[dict]:
    """Return active rows where explanation is shorter than min_length."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        query = """
            SELECT id, topic_id, concept, analogy, sources
            FROM analogies
            WHERE is_active = 1
              AND length(TRIM(explanation)) < ?
        """
        params: list = [min_length]
        if concept_filter:
            query += " AND concept = ?"
            params.append(concept_filter)
        query += " ORDER BY topic_id, concept"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


async def generate_explanation(
    topic_name: str,
    concept: str,
    analogy: str,
    sources_json: str,
) -> str:
    """Retrieve RAG context and generate only the explanation field."""
    from src.retrieval.dense_retriever import DenseRetriever
    from src.retrieval.kg_retriever import KGRetriever
    from src.llm import get_async_openai

    client = get_async_openai()

    # Use both Dense and KG retrieval for better coverage
    query = f"{topic_name}: {concept}"
    retriever = DenseRetriever()
    kg_retriever = KGRetriever()

    try:
        dense_chunks = await retriever.retrieve(query, k=10)
        kg_chunks = await kg_retriever.retrieve(query, k=8)
        # Deduplicate by content prefix
        seen: dict[str, dict] = {}
        for c in [*dense_chunks, *kg_chunks]:
            content = c.content if hasattr(c, "content") else c["content"]
            source = c.source if hasattr(c, "source") else c["source"]
            key = content[:120]
            if key not in seen:
                seen[key] = {"content": content, "source": source}
        chunks = list(seen.values())
    except Exception as e:
        logger.warning("Retrieval failed for %s: %s", concept, e)
        chunks = []

    if not chunks:
        logger.warning("No chunks found for concept=%s — explanation will be thin", concept)

    context_str = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['content']}" for c in chunks[:12]
    ) or "No relevant course context found."

    user_msg = (
        f"Topic: {topic_name}\n"
        f"Concept: {concept}\n"
        f"Analogy (for context only, do NOT repeat this): {analogy[:200]}\n\n"
        f"## Retrieved course context:\n{context_str[:3000]}"
    )

    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXPLANATION_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=350,
        temperature=0.3,
    )
    explanation = (resp.choices[0].message.content or "").strip()
    return explanation


def patch_explanation(db_path: Path, row_id: int, explanation: str, new_sources: list[str]) -> None:
    """UPDATE only the explanation (and sources if improved) for a specific row."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE analogies SET explanation = ?, sources = ? WHERE id = ?",
            (explanation, json.dumps(new_sources), row_id),
        )
        conn.commit()
    finally:
        conn.close()


async def get_topic_name(topic_id: str) -> str:
    """Look up topic name from KG."""
    from src.lms.learning_path import get_topic_by_id
    topic = get_topic_by_id(topic_id)
    return topic.name if topic else topic_id


async def main(dry_run: bool, min_length: int, concept_filter: str | None) -> None:
    rows = get_empty_rows(DB_PATH, min_length, concept_filter)

    if not rows:
        logger.info("No rows found with explanation shorter than %d chars. All good!", min_length)
        return

    logger.info(
        "Found %d rows with explanation < %d chars%s",
        len(rows),
        min_length,
        f" (filtered to '{concept_filter}')" if concept_filter else "",
    )

    for i, row in enumerate(rows, 1):
        topic_id = row["topic_id"]
        concept = row["concept"]
        current_sources = json.loads(row.get("sources") or "[]")

        logger.info("[%d/%d] %s — '%s'", i, len(rows), topic_id, concept)

        if dry_run:
            continue

        topic_name = await get_topic_name(topic_id)

        try:
            explanation = await generate_explanation(
                topic_name=topic_name,
                concept=concept,
                analogy=row.get("analogy", ""),
                sources_json=row.get("sources", "[]"),
            )
        except Exception as e:
            logger.error("Failed to generate explanation for %s/%s: %s", topic_id, concept, e)
            continue

        if not explanation or len(explanation) < 20:
            logger.warning("Got empty/thin explanation for %s/%s — skipping patch", topic_id, concept)
            continue

        # Re-run retrieval to get the source list to update (they were empty before)
        try:
            from src.retrieval.dense_retriever import DenseRetriever
            chunks = await DenseRetriever().retrieve(f"{topic_name}: {concept}", k=8)
            new_sources = list({
                c.source if hasattr(c, "source") else c["source"]
                for c in chunks
            })
        except Exception:
            new_sources = current_sources

        patch_explanation(DB_PATH, row["id"], explanation, new_sources)
        logger.info(
            "  ✓ Patched explanation (%d chars, %d sources): %s…",
            len(explanation),
            len(new_sources),
            explanation[:80],
        )

        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)

    if dry_run:
        logger.info("DRY RUN — no changes made. Re-run with --run to apply.")
    else:
        logger.info("Done. Patched %d explanations.", len(rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Patch empty Deep Dive explanations in-place.")
    parser.add_argument("--run", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument(
        "--min-length", type=int, default=30,
        help="Patch rows where explanation is shorter than this many chars (default: 30)",
    )
    parser.add_argument("--concept", type=str, default=None, help="Patch only this concept")
    args = parser.parse_args()

    asyncio.run(main(
        dry_run=not args.run,
        min_length=args.min_length,
        concept_filter=args.concept,
    ))
