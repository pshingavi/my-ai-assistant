"""Knowledge Graph visualization — Plotly interactive network graph.

Renders the TopicGraph (course modules + generated posts) as an
interactive Plotly figure suitable for Chainlit's cl.Plotly element.
"""

from __future__ import annotations

import logging

import networkx as nx
import plotly.graph_objects as go

from src.memory.topic_graph import get_topic_graph

logger = logging.getLogger(__name__)

# Node colours by source type
_COURSE_COLOR = "#7c3aed"   # purple  — bootcamp modules
_POST_COLOR = "#0ea5e9"      # blue    — generated LinkedIn posts
_EDGE_COLOR = "#6b7280"      # grey


def build_kg_figure() -> go.Figure | None:
    """Return an interactive Plotly figure of the knowledge graph.

    Returns None if the graph is empty.
    """
    kg = get_topic_graph()
    G = kg.graph

    if G.number_of_nodes() == 0:
        return None

    pos = nx.spring_layout(G, k=2.5, seed=42, iterations=60)

    # ── Edges ────────────────────────────────────────────────────────────────
    edge_x, edge_y = [], []
    for u, v in G.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1.5, color=_EDGE_COLOR),
        hoverinfo="none",
        showlegend=False,
    )

    # ── Nodes ────────────────────────────────────────────────────────────────
    course_x, course_y, course_text, course_hover = [], [], [], []
    post_x, post_y, post_text, post_hover = [], [], [], []

    for nid in G.nodes():
        if nid not in pos:
            continue
        node_data = G.nodes[nid].get("data")
        if node_data is None:
            continue
        x, y = pos[nid]
        name = node_data.name
        desc = node_data.description[:120] if node_data.description else ""
        concepts = ", ".join((node_data.concepts or [])[:4])
        hover = f"<b>{name}</b><br>{desc}<br><i>{concepts}</i>"

        if node_data.post_id:
            post_x.append(x); post_y.append(y)
            post_text.append(name[:28]); post_hover.append(hover)
        else:
            course_x.append(x); course_y.append(y)
            course_text.append(name[:28]); course_hover.append(hover)

    course_trace = go.Scatter(
        x=course_x, y=course_y,
        mode="markers+text",
        name="Course Topic",
        hovertext=course_hover,
        hoverinfo="text",
        text=course_text,
        textposition="top center",
        textfont=dict(size=11, color="white"),
        marker=dict(size=22, color=_COURSE_COLOR, line=dict(width=2, color="#a78bfa")),
    )

    post_trace = go.Scatter(
        x=post_x, y=post_y,
        mode="markers+text",
        name="Generated Post",
        hovertext=post_hover,
        hoverinfo="text",
        text=post_text,
        textposition="top center",
        textfont=dict(size=11, color="white"),
        marker=dict(size=18, color=_POST_COLOR, symbol="diamond",
                    line=dict(width=2, color="#38bdf8")),
    )

    fig = go.Figure(
        data=[edge_trace, course_trace, post_trace],
        layout=go.Layout(
            title=dict(
                text=f"GenAI Knowledge Graph — {G.number_of_nodes()} topics, {G.number_of_edges()} connections",
                font=dict(color="white", size=15),
            ),
            showlegend=True,
            legend=dict(font=dict(color="white"), bgcolor="rgba(0,0,0,0)"),
            hovermode="closest",
            paper_bgcolor="#0f0f1a",
            plot_bgcolor="#0f0f1a",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=10, r=10, t=50, b=10),
            height=600,
        ),
    )
    return fig
