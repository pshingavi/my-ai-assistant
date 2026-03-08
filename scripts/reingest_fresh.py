"""Fresh re-ingestion script — clears all KB data and rebuilds from scratch.

Deletes:
  - course_knowledge_base Qdrant collection (all course material chunks)
  - data/topic_graph.json (Knowledge Graph)

Then re-ingests all course modules and rebuilds the KG.

Usage:
    uv run python scripts/reingest_fresh.py
    uv run python scripts/reingest_fresh.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def clear_collections(dry_run: bool = False) -> None:
    """Delete and recreate the course_knowledge_base collection."""
    from dotenv import load_dotenv
    load_dotenv()

    from src.config import get_settings
    from src.memory.qdrant_store import get_qdrant_client

    cfg = get_settings()
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}

    if cfg.kb_collection in existing:
        if dry_run:
            logger.info("[DRY RUN] Would delete collection: %s", cfg.kb_collection)
        else:
            client.delete_collection(cfg.kb_collection)
            logger.info("Deleted Qdrant collection: %s", cfg.kb_collection)
    else:
        logger.info("Collection '%s' does not exist — nothing to delete", cfg.kb_collection)


def clear_topic_graph(dry_run: bool = False) -> None:
    """Delete the persisted topic graph JSON."""
    from dotenv import load_dotenv
    load_dotenv()

    from src.config import get_settings
    cfg = get_settings()
    path = cfg.kg_path

    if path.exists():
        if dry_run:
            logger.info("[DRY RUN] Would delete: %s", path)
        else:
            path.unlink()
            logger.info("Deleted topic graph: %s", path)
    else:
        logger.info("Topic graph not found at %s — nothing to delete", path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear and re-ingest all course materials")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without doing it")
    args = parser.parse_args()

    logger.info("=== FRESH RE-INGESTION ===")
    logger.info("Step 1: Clearing existing data...")
    clear_collections(dry_run=args.dry_run)
    clear_topic_graph(dry_run=args.dry_run)

    if args.dry_run:
        logger.info("[DRY RUN] Would now run: uv run python scripts/ingest_courses.py")
        return

    logger.info("Step 2: Re-ingesting all course materials...")
    # Import and run the ingestion directly (same process = same lru_cache gets cleared)
    import sys
    import importlib

    # Force clear the lru_cache on settings so fresh collection name is used
    from src.config import get_settings
    get_settings.cache_clear()
    from src.memory.qdrant_store import get_qdrant_client
    get_qdrant_client.cache_clear()

    # Also reset the topic graph singleton
    from src.memory import topic_graph as tg_mod
    tg_mod._topic_graph = None

    # Run the ingestion
    sys.argv = ["ingest_courses.py"]  # reset argv for argparse in ingest script
    import scripts.ingest_courses as ingest_mod
    importlib.reload(ingest_mod)
    asyncio.run(ingest_mod.ingest_all(ingest_mod.DEFAULT_MODULES))

    logger.info("=== RE-INGESTION COMPLETE ===")


if __name__ == "__main__":
    main()
