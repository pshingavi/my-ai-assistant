"""
Regenerate DALL-E images for all active analogies that have no image.
Skips concepts in SKIP_CONCEPTS (embeddings, HyDE already have good images).

Usage:
    uv run python scripts/regen_images.py              # dry-run
    uv run python scripts/regen_images.py --run        # actually generate
    uv run python scripts/regen_images.py --run --concurrency 3
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "analogies.db"

SKIP_CONCEPTS = {"embeddings", "HyDE"}


PUBLIC_IMAGES_DIR = ROOT / "zizi-lms" / "public" / "generated" / "images"


async def generate_image_for_concept(
    db: sqlite3.Connection,
    topic_id: str,
    concept: str,
    analogy: str,
    image_prompt: str,
    dry_run: bool,
) -> dict:
    import shutil, uuid
    from src.tools.image_tool import generate_poster

    if dry_run:
        logger.info("DRY RUN [%s] would generate image", concept)
        return {"concept": concept, "status": "dry_run"}

    try:
        _url, local_path = await generate_poster(concept, analogy, image_prompt=image_prompt or None)
        if not local_path:
            raise ValueError("no local_path returned")

        # Copy to Next.js public directory (same as analogy_pipeline does)
        PUBLIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        dest_filename = f"{uuid.uuid4().hex}.png"
        dest_path = PUBLIC_IMAGES_DIR / dest_filename
        shutil.copy2(local_path, dest_path)
        relative_url = f"/generated/images/{dest_filename}"

        db.execute(
            "UPDATE analogies SET image_url=?, image_local_path=? WHERE topic_id=? AND concept=? AND is_active=1",
            (relative_url, str(dest_path), topic_id, concept),
        )
        db.commit()
        logger.info("✓ [%s] → %s", concept, relative_url)
        return {"concept": concept, "status": "ok", "image_url": relative_url}

    except Exception as exc:
        logger.error("✗ [%s] failed: %s", concept, exc)
        return {"concept": concept, "status": "error", "error": str(exc)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()
    dry_run = not args.run

    if dry_run:
        logger.info("DRY RUN — pass --run to generate images")

    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    rows = db.execute("""
        SELECT topic_id, concept, analogy, image_prompt
        FROM analogies
        WHERE is_active=1 AND (image_url IS NULL OR image_url='')
        AND concept NOT IN ('embeddings','HyDE')
        ORDER BY concept
    """).fetchall()

    logger.info("Found %d concepts missing images", len(rows))

    sem = asyncio.Semaphore(args.concurrency)

    async def bounded(row):
        async with sem:
            return await generate_image_for_concept(
                db, row["topic_id"], row["concept"],
                row["analogy"] or "", row["image_prompt"] or "",
                dry_run,
            )

    results = await asyncio.gather(*[bounded(r) for r in rows])
    db.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    skip = sum(1 for r in results if r["status"] == "dry_run")

    print(f"\n{'='*50}")
    print(f"Images generated: {ok}/{len(rows)}")
    if err:
        print(f"Errors: {err}")
        for r in results:
            if r["status"] == "error":
                print(f"  ✗ {r['concept']}: {r.get('error','')}")
    if skip:
        print(f"Dry-run (skipped): {skip}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
