"""Chat Pipeline — LangGraph graph for Knowledge Graph RAG Q&A.

Flow: kg_retrieve → generate_answer → END

Uses KGRetriever (graph traversal + HyDE) for multi-hop context.
Responses are analogy-driven, grounded in course material and past posts.
Streaming is supported via an optional stream_handler in session context.
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.state import ChatState
from src.config import get_settings
from src.llm import get_async_openai
from src.memory.qdrant_store import ChunkResult
from src.retrieval.kg_retriever import KGRetriever

logger = logging.getLogger(__name__)

_CHAT_SYSTEM = """You are an expert AI engineering educator and LinkedIn thought leader.

Answer questions about AI/ML concepts using the retrieved context below.
Your style:
- Lead with a vivid analogy before the technical explanation
- Be accurate — only use facts present in the retrieved context
- If the context doesn't cover the question, say so honestly and suggest related topics
- Use short paragraphs, conversational tone
- End with one thought-provoking follow-up question to deepen learning

## Grounding rules:
- High-relevance chunks (score > 0.6): use as primary source, cite by name
- Medium-relevance (0.4–0.6): use to supplement, note uncertainty
- Low-relevance (< 0.4): acknowledge the gap, don't fabricate

## Retrieved context:
{context}"""


async def kg_retrieve_node(state: ChatState) -> dict:
    """Retrieve context using Knowledge Graph traversal + HyDE."""
    query = state.get("query", "")
    retriever = KGRetriever()
    chunks: list[ChunkResult] = await retriever.retrieve(query, k=get_settings().default_k)
    kb_context = [
        {"content": c.content, "score": c.score, "source": c.source, "metadata": c.metadata}
        for c in chunks
    ]
    logger.info("KG retrieved %d chunks for query=%r", len(chunks), query[:60])
    return {"retrieved_chunks": kb_context}


async def generate_answer_node(state: ChatState) -> dict:
    """Generate an analogy-driven answer grounded in retrieved context."""
    cfg = get_settings()
    client = get_async_openai()
    query = state.get("query", "")
    chunks = state.get("retrieved_chunks", [])

    context_str = "\n\n---\n\n".join(
        f"[{c['source']}, score={c['score']:.2f}]\n{c['content']}"
        for c in chunks[:6]
    )
    if not context_str:
        context_str = "No relevant context found in the knowledge base."

    response = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": _CHAT_SYSTEM.format(context=context_str)},
            {"role": "user", "content": query},
        ],
        max_tokens=700,
        temperature=0.7,
    )
    answer = response.choices[0].message.content or ""
    return {
        "response": answer,
        "messages": [AIMessage(content=answer)],
    }


def build_chat_graph() -> CompiledStateGraph:
    builder = StateGraph(ChatState)
    builder.add_node("kg_retrieve", kg_retrieve_node)
    builder.add_node("generate_answer", generate_answer_node)
    builder.add_edge(START, "kg_retrieve")
    builder.add_edge("kg_retrieve", "generate_answer")
    builder.add_edge("generate_answer", END)
    return builder.compile()
