"""
Bulk-regenerate ALL active analogies (except specified skip list) using Claude Sonnet 4.6,
then evaluate each one for simplicity, clarity, and age-appropriateness.

Usage:
    uv run python scripts/regen_analogies.py              # dry-run (show what would run)
    uv run python scripts/regen_analogies.py --run        # actually regenerate
    uv run python scripts/regen_analogies.py --run --concept "what is an LLM"  # single concept
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import textwrap
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "analogies.db"

# ── Concepts to keep as-is ──────────────────────────────────────────────────
SKIP_CONCEPTS = {"embeddings", "HyDE"}

# ── Evaluation rubric ───────────────────────────────────────────────────────
_EVAL_SYSTEM = """\
You are a learning quality evaluator. Score the following analogy for a technical concept.
Return a JSON object with these fields:
{
  "score": <1-10 integer>,
  "simplicity": <1-10>,
  "clarity": <1-10>,
  "memorability": <1-10>,
  "age_appropriate": true/false,
  "verdict": "good" | "acceptable" | "needs_work",
  "feedback": "<one short sentence>"
}

Scoring guide:
- simplicity: Can a 10-year-old understand the analogy without domain knowledge?
- clarity: Does the analogy clearly map to the technical concept?
- memorability: Is it vivid and easy to recall?
- age_appropriate: Is it relatable to learners of any age/background?
- score: Overall (average of the three sub-scores)
- verdict: good (≥8), acceptable (6-7), needs_work (<6)
"""

_ANALOGY_SYSTEM = """\
You generate simple, vivid analogies for technical AI/ML concepts. Rules:
1. Use everyday objects or situations anyone 10+ years old would know
2. No domain-specific metaphors (no orchestra conductors, no GPS systems overused)
3. One clear, concrete scene — not a multi-step metaphor
4. Max 3 sentences
5. End by connecting the analogy back to the concept in one sentence
Return ONLY the analogy text, nothing else.
"""


async def evaluate_analogy(client, concept: str, analogy: str, topic_name: str) -> dict:
    """Ask Claude to score an analogy."""
    resp = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0,
        system=_EVAL_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Concept: {concept}\nTopic: {topic_name}\nAnalogy: {analogy}"
        }],
    )
    text = resp.content[0].text.strip()
    # Strip code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"score": 0, "verdict": "parse_error", "feedback": text[:120]}


async def generate_analogy(client, concept: str, topic_name: str) -> str:
    """Generate a simple analogy for a concept."""
    resp = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-6",
        max_tokens=200,
        temperature=1,
        system=_ANALOGY_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Generate a simple analogy for: {concept} (part of {topic_name})"
        }],
    )
    return resp.content[0].text.strip()


async def process_concept(
    client,
    db: sqlite3.Connection,
    topic_id: str,
    topic_name: str,
    concept: str,
    dry_run: bool,
) -> dict:
    """Regenerate analogy for one concept, evaluate, update DB if good."""

    # --- Generate ---
    if not dry_run:
        new_analogy = await generate_analogy(client, concept, topic_name)
    else:
        new_analogy = "[DRY RUN — would generate here]"

    # --- Evaluate ---
    if not dry_run:
        eval_result = await evaluate_analogy(client, concept, new_analogy, topic_name)
    else:
        eval_result = {"score": 0, "verdict": "dry_run", "feedback": ""}

    verdict = eval_result.get("verdict", "unknown")
    score = eval_result.get("score", 0)
    feedback = eval_result.get("feedback", "")

    logger.info(
        "[%s] score=%s verdict=%s | %s",
        concept, score, verdict,
        textwrap.shorten(new_analogy, 80),
    )
    if feedback:
        logger.info("  feedback: %s", feedback)

    if dry_run:
        return {"concept": concept, "status": "dry_run", "verdict": verdict}

    if verdict == "needs_work":
        # Try once more with the feedback
        logger.info("  → re-generating with feedback: %s", feedback)
        retry_prompt = (
            f"Generate a simple analogy for: {concept} (part of {topic_name})\n\n"
            f"Previous attempt was rejected because: {feedback}\n"
            "Try a completely different everyday scene."
        )
        resp = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=200,
            temperature=1,
            system=_ANALOGY_SYSTEM,
            messages=[{"role": "user", "content": retry_prompt}],
        )
        new_analogy = resp.content[0].text.strip()
        eval_result = await evaluate_analogy(client, concept, new_analogy, topic_name)
        verdict = eval_result.get("verdict", "unknown")
        score = eval_result.get("score", 0)
        logger.info("  → retry score=%s verdict=%s", score, verdict)

    # --- Persist (mark old inactive, insert new active) ---
    db.execute(
        "UPDATE analogies SET is_active=0 WHERE topic_id=? AND concept=?",
        (topic_id, concept),
    )
    db.execute(
        """INSERT INTO analogies
           (topic_id, concept, analogy, is_active, version)
           VALUES (?, ?, ?, 1,
             COALESCE((SELECT MAX(version)+1 FROM analogies WHERE topic_id=? AND concept=?), 1))
        """,
        (topic_id, concept, new_analogy, topic_id, concept),
    )
    db.commit()

    return {
        "concept": concept,
        "status": "updated",
        "verdict": verdict,
        "score": score,
        "analogy": new_analogy,
        "feedback": feedback,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Actually regenerate (default: dry-run)")
    parser.add_argument("--concept", default="", help="Regenerate only this concept")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel workers")
    args = parser.parse_args()

    dry_run = not args.run

    if dry_run:
        logger.info("DRY RUN mode — pass --run to actually regenerate")

    import anthropic
    from src.config import get_settings
    cfg = get_settings()
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    # Load all active bytes (topic_id + topic_name from analogies table)
    rows = db.execute("""
        SELECT DISTINCT a.topic_id, a.concept, a.analogy
        FROM analogies a
        WHERE a.is_active = 1
        ORDER BY a.topic_id, a.concept
    """).fetchall()

    # Load topic names from the KG
    import json as _json
    kg_path = ROOT / "data" / "topic_graph.json"
    topic_names: dict[str, str] = {}
    if kg_path.exists():
        kg = _json.loads(kg_path.read_text())
        for node in kg.get("nodes", []):
            topic_names[node["id"]] = node.get("name", node["id"])

    # Filter
    targets = []
    for row in rows:
        concept = row["concept"]
        if concept in SKIP_CONCEPTS:
            logger.info("SKIP: %s (in skip list)", concept)
            continue
        if args.concept and concept.lower() != args.concept.lower():
            continue
        topic_name = topic_names.get(row["topic_id"], row["topic_id"])
        targets.append((row["topic_id"], topic_name, concept))

    logger.info("Will process %d concepts (skipping %s)", len(targets), SKIP_CONCEPTS)

    # Process with semaphore to limit concurrency
    sem = asyncio.Semaphore(args.concurrency)
    results = []

    async def bounded(tid, tname, concept):
        async with sem:
            return await process_concept(client, db, tid, tname, concept, dry_run)

    tasks = [bounded(tid, tname, c) for tid, tname, c in targets]
    results = await asyncio.gather(*tasks)

    db.close()

    # Summary
    print("\n" + "="*60)
    print(f"RESULTS ({len(results)} concepts)")
    print("="*60)
    by_verdict: dict[str, list] = {}
    for r in results:
        by_verdict.setdefault(r["verdict"], []).append(r)

    for verdict, items in sorted(by_verdict.items()):
        print(f"\n[{verdict.upper()}] — {len(items)} concepts")
        for item in items:
            score_str = f" score={item.get('score','?')}" if "score" in item else ""
            print(f"  • {item['concept']}{score_str}")
            if item.get("feedback"):
                print(f"    {item['feedback']}")

    needs_work = by_verdict.get("needs_work", [])
    if needs_work:
        print(f"\n⚠️  {len(needs_work)} concepts still need manual review")
        sys.exit(1)
    else:
        print("\n✅ All analogies passed evaluation")


if __name__ == "__main__":
    asyncio.run(main())
