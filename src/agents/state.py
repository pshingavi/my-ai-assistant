"""LangGraph state definitions for both pipelines."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.tools.tavily_tool import TopicResult


class ContentState(TypedDict):
    """State for the Content Creation pipeline."""
    # Input
    domain: str
    user_request: str
    # Research
    tavily_topics: list[TopicResult]
    x_topics: list[TopicResult]
    selected_topic: str
    topic_description: str
    # Dedup
    is_duplicate: bool
    duplicate_reason: str
    # RAG context
    kb_context: list[dict[str, Any]]
    # Generated content
    linkedin_post: str
    image_prompt: str
    image_url: str
    image_local_path: str
    analogy_summary: str
    # Control
    messages: Annotated[list[AnyMessage], add_messages]
    error: str


class ChatState(TypedDict):
    """State for the Chat (Knowledge Graph RAG) pipeline."""
    query: str
    retrieved_chunks: list[dict[str, Any]]
    response: str
    messages: Annotated[list[AnyMessage], add_messages]
