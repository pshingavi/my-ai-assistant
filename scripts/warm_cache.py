"""CLI script to pre-generate all topic bytes and fill the SQLite analogy cache.

Usage:
    uv run python scripts/warm_cache.py              # all topics
    uv run python scripts/warm_cache.py --modules 03,05  # subset by module number
    uv run python scripts/warm_cache.py --dry-run    # list what would run
    uv run python scripts/warm_cache.py --skip-images  # skip DALL-E generation (faster dev)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` is importable when run directly.
_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("warm_cache")

_DB_PATH = str(_PROJECT_ROOT / "data" / "analogies.db")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pre-generate analogy bytes for all LMS topics into the SQLite cache."
    )
    parser.add_argument(
        "--modules",
        metavar="NUMS",
        default="",
        help="Comma-separated module numbers to warm, e.g. 03,05. Default: all.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without actually calling the LLM.",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip DALL-E image generation (faster for dev / testing).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all bytes, even if already cached.",
    )
    return parser.parse_args()


async def _main(args: argparse.Namespace) -> None:
    from src.lms.analogy_store import get_active_byte, init_db
    from src.lms.analogy_pipeline import run_byte_pipeline
    from src.lms.learning_path import get_all_topics

    await init_db(_DB_PATH)

    topics = get_all_topics()

    # Filter by module number if requested
    module_filter: set[str] = set()
    if args.modules:
        module_filter = {m.strip().lstrip("0") or "0" for m in args.modules.split(",")}

    if module_filter:
        topics = [
            t for t in topics
            if (t.module_number.lstrip("0") or "0") in module_filter
        ]
        logger.info("Filtering to modules %s — %d topics matched", args.modules, len(topics))

    # Build work list: (topic, concept) pairs not yet cached
    work: list[tuple] = []
    skip_count = 0
    for topic in topics:
        for concept in topic.concepts:
            existing = await get_active_byte(topic.id, concept, db_path=_DB_PATH)
            if existing and not args.force:
                skip_count += 1
                continue
            work.append((topic, concept))

    total = len(work) + skip_count
    logger.info(
        "Cache status: %d total combos, %d already cached, %d to generate",
        total,
        skip_count,
        len(work),
    )

    if args.dry_run:
        if not work:
            logger.info("DRY RUN: nothing to generate — cache is fully warm.")
            return
        logger.info("DRY RUN — would generate %d bytes:", len(work))
        for topic, concept in work:
            print(f"  [{topic.module_number or '?'}] {topic.name} / {concept}")
        return

    if not work:
        logger.info("All bytes already cached. Nothing to do.")
        return

    # Optionally patch out the image agent to avoid DALL-E calls
    if args.skip_images:
        logger.info("--skip-images: image generation will be skipped.")
        _patch_image_agent()

    succeeded = 0
    failed = 0
    for idx, (topic, concept) in enumerate(work, start=1):
        logger.info(
            "[%d/%d] Generating: [%s] %s / %s",
            idx,
            len(work),
            topic.module_number or "?",
            topic.name,
            concept,
        )
        try:
            result = await run_byte_pipeline(
                topic_id=topic.id,
                topic_name=topic.name,
                concept=concept,
                force_regenerate=args.force,
                db_path=_DB_PATH,
            )
            emoji = result.get("emoji", "")
            analogy_preview = (result.get("analogy") or "")[:60]
            logger.info("  OK  %s  %s…", emoji, analogy_preview)
            succeeded += 1
        except Exception as exc:
            logger.warning("  FAIL  %s / %s: %s", topic.name, concept, exc)
            failed += 1

    logger.info(
        "Done. %d succeeded, %d failed out of %d attempted.",
        succeeded,
        failed,
        len(work),
    )


def _patch_image_agent() -> None:
    """Monkey-patch the image_agent_node to be a no-op (skip DALL-E)."""
    import src.lms.analogy_pipeline as pipeline

    async def _noop_image(state):
        logger.debug("skip-images: image generation skipped for %s", state.get("concept"))
        return {"image_url": "", "image_local_path": ""}

    pipeline.image_agent_node = _noop_image  # type: ignore[assignment]
    logger.info("Image agent patched to no-op.")


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(_main(args))
