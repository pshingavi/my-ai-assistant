"""Retriever protocol — all retrieval strategies implement this interface.

Follows the Dependency Inversion Principle: callers depend on the Retriever
protocol, not on a specific implementation (dense, HyDE, KG, etc.).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.memory.qdrant_store import ChunkResult


@runtime_checkable
class Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        """Retrieve the top-k most relevant chunks for a query."""
        ...
