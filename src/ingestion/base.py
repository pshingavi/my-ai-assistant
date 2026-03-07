"""Base ingester protocol — all ingesters implement this interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Ingester(Protocol):
    async def ingest(self, source: Path | str, metadata: dict[str, Any] | None = None) -> int:
        """Ingest source into the vector store. Returns number of chunks upserted."""
        ...
