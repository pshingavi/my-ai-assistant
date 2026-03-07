"""Knowledge Graph over AI topics — persisted as JSON, powered by NetworkX.

Structure
---------
Nodes: topics and concepts extracted from each generated LinkedIn post.
Edges: directed relationships (USES, EXTENDS, CONTRASTS, REQUIRES, RELATED_TO).

KG Retrieval flow:
  1. Embed the query.
  2. Cosine-similarity match against node embeddings → find seed topics.
  3. Traverse edges up to kg_max_hops to collect related topic names.
  4. Use those names as additional filter queries against Qdrant.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class TopicNode:
    id: str
    name: str
    description: str
    concepts: list[str]
    post_id: str | None = None
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "concepts": self.concepts,
            "post_id": self.post_id,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TopicNode:
        return cls(**d)


class TopicGraph:
    """NetworkX-backed knowledge graph with JSON persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._graph: nx.DiGraph = nx.DiGraph()
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                for node_data in data.get("nodes", []):
                    node = TopicNode.from_dict(node_data)
                    self._graph.add_node(node.id, data=node)
                for edge in data.get("edges", []):
                    self._graph.add_edge(
                        edge["source"], edge["target"], relation=edge["relation"]
                    )
                logger.info(
                    "Loaded KG: %d nodes, %d edges",
                    self._graph.number_of_nodes(),
                    self._graph.number_of_edges(),
                )
            except Exception:
                logger.warning("Failed to load KG from %s — starting fresh", self._path, exc_info=True)

    def save(self) -> None:
        nodes = [
            self._graph.nodes[nid]["data"].to_dict()
            for nid in self._graph.nodes
        ]
        edges = [
            {"source": u, "target": v, "relation": d.get("relation", "RELATED_TO")}
            for u, v, d in self._graph.edges(data=True)
        ]
        self._path.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=2))

    # ── Write operations ──────────────────────────────────────────────────────

    def add_topic(self, node: TopicNode, related_to: list[str] | None = None) -> None:
        """Add a topic node and optional edges to existing topic names."""
        self._graph.add_node(node.id, data=node)

        if related_to:
            for name in related_to:
                existing_id = self._find_by_name(name)
                if existing_id and existing_id != node.id:
                    self._graph.add_edge(node.id, existing_id, relation="RELATED_TO")

        self.save()
        logger.info("Added topic '%s' to KG", node.name)

    def connect_by_name(self, from_name: str, to_name: str, relation: str = "BUILDS_ON") -> bool:
        """Create a directed edge between two nodes identified by name."""
        from_id = self._find_by_name(from_name)
        to_id = self._find_by_name(to_name)
        if from_id and to_id and from_id != to_id:
            self._graph.add_edge(from_id, to_id, relation=relation)
            return True
        return False

    def _find_by_name(self, name: str) -> str | None:
        for nid in self._graph.nodes:
            node: TopicNode = self._graph.nodes[nid]["data"]
            if node.name.lower() == name.lower():
                return nid
        return None

    # ── Read operations ───────────────────────────────────────────────────────

    def find_related_topics(
        self, query_embedding: list[float], top_k: int = 3, max_hops: int = 2
    ) -> list[str]:
        """Return topic names reachable from the best-matching seed nodes."""
        if not self._graph.nodes:
            return []

        # 1. Find seed nodes by cosine similarity
        seeds = self._top_k_by_embedding(query_embedding, k=top_k)

        # 2. Traverse up to max_hops
        visited: set[str] = set(seeds)
        frontier = set(seeds)
        for _ in range(max_hops):
            next_frontier: set[str] = set()
            for nid in frontier:
                neighbors = set(self._graph.successors(nid)) | set(
                    self._graph.predecessors(nid)
                )
                next_frontier |= neighbors - visited
            visited |= next_frontier
            frontier = next_frontier

        # 3. Return unique topic names
        names = []
        for nid in visited:
            node: TopicNode = self._graph.nodes[nid]["data"]
            names.append(node.name)
        return names

    def _top_k_by_embedding(self, query: list[float], k: int) -> list[str]:
        """Return the node IDs of the k closest nodes by cosine similarity."""
        scored = []
        for nid in self._graph.nodes:
            node: TopicNode = self._graph.nodes[nid]["data"]
            if node.embedding:
                sim = _cosine(query, node.embedding)
                scored.append((sim, nid))
        scored.sort(reverse=True)
        return [nid for _, nid in scored[:k]]

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    def all_topic_names(self) -> list[str]:
        return [
            self._graph.nodes[nid]["data"].name for nid in self._graph.nodes
        ]

    def stats(self) -> dict[str, int]:
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
        }


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Singleton ─────────────────────────────────────────────────────────────────

_graph_instance: TopicGraph | None = None


def get_topic_graph() -> TopicGraph:
    global _graph_instance
    if _graph_instance is None:
        from src.config import get_settings
        _graph_instance = TopicGraph(get_settings().kg_path)
    return _graph_instance
