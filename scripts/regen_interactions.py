"""
Pre-generate Claude interactions for all active concepts that don't have one cached.
Retries each failed concept up to MAX_RETRIES times before marking as permanently failed.

Usage:
    uv run python scripts/regen_interactions.py          # dry-run
    uv run python scripts/regen_interactions.py --run    # generate & save
    uv run python scripts/regen_interactions.py --run --concurrency 3
    uv run python scripts/regen_interactions.py --run --force  # regenerate even if cached
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "analogies.db"
MAX_RETRIES = 3


async def generate_one(generator, topic_id: str, topic_name: str, concept: str, analogy: str) -> dict:
    """Single attempt to generate and save one interaction. Returns result dict."""
    from src.lms.analogy_store import save_claude_interaction

    result = await generator.generate(
        concept=concept,
        analogy=analogy,
        topic_name=topic_name,
        rag_context=None,
    )
    sketch_code = result.get("sketch_code", "")
    steps = result.get("steps", [])

    if not sketch_code or len(sketch_code) < 500:
        raise ValueError(f"sketch too short ({len(sketch_code)} chars)")

    await save_claude_interaction(
        topic_id=topic_id,
        concept=concept,
        sketch_code=sketch_code,
        steps_json=steps,
        analogy=analogy,
        db_path=str(DB_PATH),
    )
    return {"concept": concept, "status": "ok", "size": len(sketch_code), "steps": len(steps)}


async def process_with_retry(
    generator,
    topic_id: str,
    topic_name: str,
    concept: str,
    analogy: str,
) -> dict:
    """Try up to MAX_RETRIES times with exponential backoff."""
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = await generate_one(generator, topic_id, topic_name, concept, analogy)
            if attempt > 1:
                logger.info("✓ [%s] OK on attempt %d (%d chars, %d steps)", concept, attempt, r["size"], r["steps"])
            else:
                logger.info("✓ [%s] saved %d chars, %d steps", concept, r["size"], r["steps"])
            return r
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                wait = 5 * attempt  # 5s, 10s backoff
                logger.warning("✗ [%s] attempt %d/%d failed: %s — retrying in %ds",
                               concept, attempt, MAX_RETRIES, exc, wait)
                await asyncio.sleep(wait)
            else:
                logger.error("✗ [%s] FAILED after %d attempts: %s", concept, MAX_RETRIES, exc)

    return {"concept": concept, "status": "failed", "error": last_error, "attempts": MAX_RETRIES}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate even if already cached")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--concept", default="", help="Process only this concept")
    args = parser.parse_args()
    dry_run = not args.run

    if dry_run:
        logger.info("DRY RUN — pass --run to generate")

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    # Load topic names from KG
    import json as _json
    kg_path = ROOT / "data" / "topic_graph.json"
    topic_names: dict[str, str] = {}
    if kg_path.exists():
        kg = _json.loads(kg_path.read_text())
        for node in kg.get("nodes", []):
            topic_names[node["id"]] = node.get("name", node["id"])

    # Find already-cached concepts (by topic_id+concept pair)
    cached_pairs = set(
        (row[0], row[1])
        for row in db.execute("SELECT topic_id, concept FROM claude_interactions").fetchall()
    )

    # Load all active analogies
    rows = db.execute("""
        SELECT topic_id, concept, analogy
        FROM analogies WHERE is_active=1
        ORDER BY topic_id, concept
    """).fetchall()

    targets = []
    skipped = 0
    for row in rows:
        concept = row["concept"]
        topic_id = row["topic_id"]
        if args.concept and concept.lower() != args.concept.lower():
            continue
        if not args.force and (topic_id, concept) in cached_pairs:
            skipped += 1
            continue
        topic_name = topic_names.get(topic_id, topic_id)
        targets.append((topic_id, topic_name, concept, row["analogy"] or ""))

    logger.info("Will generate %d interactions | Already cached: %d | Total: %d",
                len(targets), skipped, len(rows))

    if not targets:
        print("Nothing to generate.")
        db.close()
        return

    db.close()

    if dry_run:
        for t in targets:
            logger.info("  would generate: [%s] (topic: %s)", t[2], t[1])
        print(f"\nDry-run: {len(targets)} concepts would be generated.")
        return

    from src.lms.claude_interaction_generator import ClaudeInteractionGenerator
    generator = ClaudeInteractionGenerator()

    sem = asyncio.Semaphore(args.concurrency)
    start = time.time()

    async def bounded(tid, tname, concept, analogy):
        async with sem:
            return await process_with_retry(generator, tid, tname, concept, analogy)

    results = await asyncio.gather(*[bounded(*t) for t in targets])

    elapsed = time.time() - start
    ok      = [r for r in results if r["status"] == "ok"]
    failed  = [r for r in results if r["status"] == "failed"]

    print(f"\n{'='*60}")
    print(f"DONE in {elapsed/60:.1f} min")
    print(f"  Generated : {len(ok)}")
    print(f"  Skipped   : {skipped} (already cached)")
    print(f"  Failed    : {len(failed)}")

    if failed:
        print(f"\nFAILED CONCEPTS (after {MAX_RETRIES} attempts each):")
        for r in failed:
            print(f"  ✗ [{r['concept']}] — {r.get('error','')[:100]}")
        print("\nTo retry failed ones:")
        for r in failed:
            print(f"  uv run python scripts/regen_interactions.py --run --concept \"{r['concept']}\"")
    else:
        print("\n✅ All interactions generated successfully!")


if __name__ == "__main__":
    asyncio.run(main())
