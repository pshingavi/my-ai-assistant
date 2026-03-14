"""Single source of truth for all application settings.

All values are read from environment variables or a .env file.
Override any value by setting the corresponding env var before startup.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "AI Content Creator"
    content_domain: str = "Generative AI"

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # ── Image Generation ──────────────────────────────────────────────────────
    image_model: str = "gpt-image-1"
    image_size: str = "1024x1024"
    image_quality: str = "high"
    images_dir: str = "data/images"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    kb_collection: str = "course_knowledge_base"
    posts_collection: str = "generated_posts"

    # ── Tavily ────────────────────────────────────────────────────────────────
    tavily_api_key: str
    tavily_max_results: int = 5

    # ── X / Twitter ───────────────────────────────────────────────────────────
    x_bearer_token: str | None = None
    x_max_results: int = 10

    # ── LangSmith ─────────────────────────────────────────────────────────────
    langchain_tracing_v2: str = "false"
    langchain_api_key: str | None = None
    langchain_project: str = "ai-content-creator"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ── Agent tuning ──────────────────────────────────────────────────────────
    relevance_threshold: float = 0.50
    dedup_threshold: float = 0.85
    default_k: int = 5
    hyde_enabled: bool = True
    hyde_max_tokens: int = 512

    # ── Knowledge Graph ───────────────────────────────────────────────────────
    kg_graph_path: str = "data/topic_graph.json"
    kg_max_hops: int = 2

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── Cohere ────────────────────────────────────────────────────────────────
    cohere_api_key: str | None = None

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 50

    def configure_langsmith(self) -> None:
        """Set LangSmith env vars so LangGraph auto-traces when key is present."""
        if self.langchain_api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project
            os.environ["LANGCHAIN_ENDPOINT"] = self.langchain_endpoint

    @property
    def images_path(self) -> Path:
        p = Path(self.images_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def kg_path(self) -> Path:
        p = Path(self.kg_graph_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
