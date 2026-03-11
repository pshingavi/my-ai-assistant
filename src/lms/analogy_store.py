"""SQLite-backed long-term memory store for analogy content.

Schema:
  analogies — one row per (topic_id, concept, version)
              is_active=1 marks the current live version
  warm_jobs  — pre-generation job tracking
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CREATE_ANALOGIES = """
CREATE TABLE IF NOT EXISTS analogies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id        TEXT    NOT NULL,
    concept         TEXT    NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    analogy         TEXT    NOT NULL DEFAULT '',
    explanation     TEXT    NOT NULL DEFAULT '',
    why_it_matters  TEXT    NOT NULL DEFAULT '',
    emoji           TEXT    NOT NULL DEFAULT '🧠',
    image_prompt    TEXT    NOT NULL DEFAULT '',
    image_url       TEXT    NOT NULL DEFAULT '',
    image_local_path TEXT   NOT NULL DEFAULT '',
    animation_props TEXT    NOT NULL DEFAULT '{}',
    sources         TEXT    NOT NULL DEFAULT '[]',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    is_active       INTEGER NOT NULL DEFAULT 1
);
"""

_CREATE_ANALOGY_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_analogy_lookup ON analogies(topic_id, concept, is_active);
CREATE INDEX IF NOT EXISTS idx_analogy_history ON analogies(topic_id, concept, version);
"""

_CREATE_WARM_JOBS = """
CREATE TABLE IF NOT EXISTS warm_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id    TEXT NOT NULL,
    concept     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    error       TEXT NOT NULL DEFAULT '',
    started_at  TEXT,
    finished_at TEXT,
    UNIQUE(topic_id, concept)
);
"""

_CREATE_WARM_JOBS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_warm_status ON warm_jobs(status);
"""


async def init_db(db_path: str) -> None:
    """Create tables and indexes idempotently. Creates DB file if not present."""
    import aiosqlite

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_ANALOGIES)
        for stmt in _CREATE_ANALOGY_INDEXES.strip().splitlines():
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.execute(_CREATE_WARM_JOBS)
        for stmt in _CREATE_WARM_JOBS_INDEX.strip().splitlines():
            stmt = stmt.strip()
            if stmt:
                await db.execute(stmt)
        await db.commit()
    logger.info("analogy_store: DB initialised at %s", db_path)


def _row_to_dict(row: Any, cursor: Any) -> dict:
    """Convert an aiosqlite Row to a plain dict using column names."""
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


async def get_active_byte(topic_id: str, concept: str, db_path: str = "data/analogies.db") -> dict | None:
    """Fast indexed lookup for the currently active analogy row.

    Returns the row as a dict, or None if not found.
    """
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT * FROM analogies WHERE topic_id=? AND concept=? AND is_active=1 LIMIT 1",
            (topic_id, concept),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            result = _row_to_dict(row, cursor)

    # Deserialise JSON fields
    result["animation_props"] = json.loads(result.get("animation_props") or "{}")
    result["sources"] = json.loads(result.get("sources") or "[]")
    return result


async def get_version_history(
    topic_id: str, concept: str, db_path: str = "data/analogies.db"
) -> list[dict]:
    """Return all versions for a (topic_id, concept) pair, newest first."""
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT * FROM analogies WHERE topic_id=? AND concept=? ORDER BY version DESC",
            (topic_id, concept),
        ) as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return []
            results = [_row_to_dict(r, cursor) for r in rows]

    for r in results:
        r["animation_props"] = json.loads(r.get("animation_props") or "{}")
        r["sources"] = json.loads(r.get("sources") or "[]")
    return results


async def save_byte(
    topic_id: str,
    concept: str,
    data: dict,
    db_path: str = "data/analogies.db",
) -> int:
    """Persist a new byte row and retire the previous active version.

    Returns the new row id.
    If an active row exists: sets is_active=0 on it, increments version.
    Inserts new row with is_active=1.
    """
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        # Find current active version
        async with db.execute(
            "SELECT version FROM analogies WHERE topic_id=? AND concept=? AND is_active=1 LIMIT 1",
            (topic_id, concept),
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            current_version = existing[0]
            new_version = current_version + 1
            await db.execute(
                "UPDATE analogies SET is_active=0 WHERE topic_id=? AND concept=? AND is_active=1",
                (topic_id, concept),
            )
        else:
            new_version = 1

        # Serialise compound fields
        animation_props = data.get("animation_props", {})
        sources = data.get("sources", [])
        if isinstance(animation_props, dict):
            animation_props = json.dumps(animation_props)
        if isinstance(sources, list):
            sources = json.dumps(sources)

        cursor = await db.execute(
            """INSERT INTO analogies
               (topic_id, concept, version, analogy, explanation, why_it_matters,
                emoji, image_prompt, image_url, image_local_path, animation_props,
                sources, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                topic_id,
                concept,
                new_version,
                data.get("analogy", ""),
                data.get("explanation", ""),
                data.get("why_it_matters", ""),
                data.get("emoji", "🧠"),
                data.get("image_prompt", ""),
                data.get("image_url", ""),
                data.get("image_local_path", ""),
                animation_props,
                sources,
            ),
        )
        new_id = cursor.lastrowid
        await db.commit()

    logger.info(
        "analogy_store: saved byte id=%s topic=%s concept=%s version=%s",
        new_id,
        topic_id,
        concept,
        new_version,
    )
    return new_id  # type: ignore[return-value]


async def get_warm_status(db_path: str = "data/analogies.db") -> dict:
    """Return counts of warm_jobs grouped by status."""
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT status, COUNT(*) FROM warm_jobs GROUP BY status"
        ) as cursor:
            rows = await cursor.fetchall()

    counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
    for status, count in rows:
        counts[status] = count
    return counts


async def upsert_warm_job(
    topic_id: str,
    concept: str,
    status: str,
    error: str = "",
    db_path: str = "data/analogies.db",
) -> None:
    """Insert or update a warm_jobs row for (topic_id, concept)."""
    import aiosqlite

    async with aiosqlite.connect(db_path) as db:
        if status == "running":
            await db.execute(
                """INSERT INTO warm_jobs (topic_id, concept, status, error, started_at)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(topic_id, concept) DO UPDATE SET
                     status=excluded.status,
                     error=excluded.error,
                     started_at=datetime('now')""",
                (topic_id, concept, status, error),
            )
        elif status in ("done", "failed"):
            await db.execute(
                """INSERT INTO warm_jobs (topic_id, concept, status, error, finished_at)
                   VALUES (?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(topic_id, concept) DO UPDATE SET
                     status=excluded.status,
                     error=excluded.error,
                     finished_at=datetime('now')""",
                (topic_id, concept, status, error),
            )
        else:
            await db.execute(
                """INSERT INTO warm_jobs (topic_id, concept, status, error)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(topic_id, concept) DO UPDATE SET
                     status=excluded.status,
                     error=excluded.error""",
                (topic_id, concept, status, error),
            )
        await db.commit()
