"""LLM and embedding client factory.

All callers should use the getter functions — never instantiate clients directly.
This ensures settings changes propagate consistently and clients are reused.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import AsyncOpenAI

from src.config import get_settings


@lru_cache
def get_async_openai() -> AsyncOpenAI:
    """Raw async OpenAI client — used for streaming and image generation."""
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


@lru_cache
def get_chat_llm(model: str | None = None) -> ChatOpenAI:
    """LangChain ChatOpenAI — used in LangGraph nodes and RAGAS."""
    cfg = get_settings()
    return ChatOpenAI(
        model=model or cfg.llm_model,
        openai_api_key=cfg.openai_api_key,
        temperature=0.7,
    )


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """LangChain OpenAI embeddings — used in retrieval and RAGAS."""
    cfg = get_settings()
    return OpenAIEmbeddings(
        model=cfg.embedding_model,
        openai_api_key=cfg.openai_api_key,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts and return their vectors."""
    client = get_async_openai()
    cfg = get_settings()
    response = await client.embeddings.create(model=cfg.embedding_model, input=texts)
    return [item.embedding for item in response.data]
