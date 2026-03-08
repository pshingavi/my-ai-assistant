"""Learning path utilities — navigate the topic Knowledge Graph.

Provides topological ordering of topics and neighbour traversal so the
LMS frontend can show "what to learn next" and "what this builds on".
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


@dataclass
class TopicSummary:
    id: str
    name: str
    description: str
    concepts: list[str]
    module_number: str
    source_url: str
    is_post: bool  # True when node was generated from content pipeline


def _get_kg() -> Any:
    from src.memory.topic_graph import get_topic_graph
    return get_topic_graph()


def _node_to_summary(node_data: Any) -> TopicSummary:
    return TopicSummary(
        id=node_data.id,
        name=node_data.name,
        description=node_data.description,
        concepts=node_data.concepts,
        module_number=getattr(node_data, "module_number", ""),
        source_url=getattr(node_data, "source_url", ""),
        is_post=node_data.post_id is not None,
    )


def get_all_topics() -> list[TopicSummary]:
    """Return all KG nodes sorted by module number (course topics first)."""
    kg = _get_kg()
    summaries: list[TopicSummary] = []
    for nid in kg.graph.nodes:
        node = kg.graph.nodes[nid]["data"]
        summaries.append(_node_to_summary(node))

    # Course modules first (sorted numerically), then generated posts
    def _sort_key(s: TopicSummary) -> tuple[int, str]:
        try:
            return (0, f"{int(s.module_number):04d}") if s.module_number else (1, s.name)
        except ValueError:
            return (1, s.name)

    summaries.sort(key=_sort_key)
    return summaries


def get_topic_by_id(topic_id: str) -> TopicSummary | None:
    """Return a single topic by its node ID."""
    kg = _get_kg()
    if topic_id not in kg.graph.nodes:
        return None
    node = kg.graph.nodes[topic_id]["data"]
    return _node_to_summary(node)


def get_topic_neighbors(topic_id: str) -> dict[str, list[TopicSummary]]:
    """Return topics directly connected to this node.

    Returns a dict with keys:
      - "prerequisites"  — nodes with an edge pointing TO this topic
      - "next"           — nodes this topic points TO (what to learn next)
      - "related"        — bidirectional RELATED_TO neighbours
    """
    kg = _get_kg()
    if topic_id not in kg.graph.nodes:
        return {"prerequisites": [], "next": [], "related": []}

    prerequisites: list[TopicSummary] = []
    next_topics: list[TopicSummary] = []
    related: list[TopicSummary] = []

    for pred_id in kg.graph.predecessors(topic_id):
        edge_data = kg.graph.edges[pred_id, topic_id]
        relation = edge_data.get("relation", "RELATED_TO")
        node = kg.graph.nodes[pred_id]["data"]
        summary = _node_to_summary(node)
        if relation in ("BUILDS_ON", "REQUIRES"):
            prerequisites.append(summary)
        else:
            related.append(summary)

    for succ_id in kg.graph.successors(topic_id):
        edge_data = kg.graph.edges[topic_id, succ_id]
        relation = edge_data.get("relation", "RELATED_TO")
        node = kg.graph.nodes[succ_id]["data"]
        summary = _node_to_summary(node)
        if relation in ("BUILDS_ON", "REQUIRES"):
            next_topics.append(summary)
        else:
            related.append(summary)

    return {"prerequisites": prerequisites, "next": next_topics, "related": related}


def get_learning_order() -> list[TopicSummary]:
    """Topological sort of course topics (prerequisites before dependents).

    Falls back to module-number ordering if cycles exist.
    """
    kg = _get_kg()
    try:
        topo_ids = list(nx.topological_sort(kg.graph))
        result = []
        for nid in topo_ids:
            node = kg.graph.nodes[nid]["data"]
            result.append(_node_to_summary(node))
        return result
    except nx.NetworkXUnfeasible:
        logger.warning("KG has cycles — falling back to module order")
        return get_all_topics()


def get_kg_graph_data() -> dict[str, list[dict]]:
    """Serialise the full KG for D3 / Plotly rendering in the frontend."""
    kg = _get_kg()
    nodes = []
    for nid in kg.graph.nodes:
        node = kg.graph.nodes[nid]["data"]
        nodes.append({
            "id": node.id,
            "name": node.name,
            "description": node.description,
            "concepts": node.concepts,
            "module_number": getattr(node, "module_number", ""),
            "source_url": getattr(node, "source_url", ""),
            "is_post": node.post_id is not None,
        })

    edges = []
    for u, v, data in kg.graph.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", "RELATED_TO"),
        })

    return {"nodes": nodes, "edges": edges}
