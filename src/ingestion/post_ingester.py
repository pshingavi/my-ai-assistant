"""Post ingester — stores generated LinkedIn posts + topic metadata in Qdrant.

Also updates the Knowledge Graph with topic nodes and relationships.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.config import get_settings
from src.llm import embed_texts, get_async_openai
from src.memory.qdrant_store import ensure_collection, upsert_chunks
from src.memory.topic_graph import TopicNode, get_topic_graph

logger = logging.getLogger(__name__)


@dataclass
class GeneratedPost:
    topic: str
    post_text: str
    image_url: str
    image_path: str
    analogy_summary: str = ""
    concepts: list[str] | None = None
    post_id: str | None = None
    source_media_urls: list[str] | None = None  # images/videos from X.com source tweets

    def __post_init__(self) -> None:
        self.post_id = self.post_id or str(uuid.uuid4())
        self.concepts = self.concepts or []


class PostIngester:
    """Ingest a GeneratedPost into Qdrant and the topic Knowledge Graph."""

    def __init__(self, collection: str | None = None) -> None:
        self._collection = collection or get_settings().posts_collection

    async def ingest(self, post: GeneratedPost) -> int:
        # 1. Chunk the post text
        chunks = [post.post_text]
        metadata = [
            {
                "source_type": "linkedin_post",
                "source": post.topic,
                "topic": post.topic,
                "post_id": post.post_id,
                "image_url": post.image_url,
                "media_urls": post.source_media_urls or [],
                "created_at": datetime.utcnow().isoformat(),
            }
        ]
        ensure_collection(self._collection)
        vectors = await embed_texts(chunks)
        n = upsert_chunks(self._collection, chunks, vectors, metadata)

        # 2. Update the Knowledge Graph
        await self._update_kg(post, vectors[0])

        return n

    async def _update_kg(self, post: GeneratedPost, embedding: list[float]) -> None:
        try:
            # Extract related concepts via LLM if not provided
            concepts = post.concepts or await self._extract_concepts(post.topic, post.post_text)

            node = TopicNode(
                id=str(uuid.uuid4()),
                name=post.topic,
                description=post.analogy_summary or post.post_text[:200],
                concepts=concepts,
                post_id=post.post_id,
                embedding=embedding,
            )
            kg = get_topic_graph()
            kg.add_topic(node, related_to=concepts[:5])
            logger.info("KG updated: added topic '%s' with %d concepts", post.topic, len(concepts))
        except Exception:
            logger.warning("KG update failed for topic '%s'", post.topic, exc_info=True)

    async def _extract_concepts(self, topic: str, post_text: str) -> list[str]:
        """Use LLM to extract 5-7 related AI concepts from the post."""
        cfg = get_settings()
        client = get_async_openai()
        prompt = (
            f"Given this LinkedIn post about '{topic}', list 5-7 related AI/ML concepts "
            f"mentioned or implied. Return ONLY a comma-separated list of concept names.\n\n"
            f"Post:\n{post_text[:800]}"
        )
        try:
            response = await client.chat.completions.create(
                model=cfg.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            raw = response.choices[0].message.content or ""
            return [c.strip() for c in raw.split(",") if c.strip()][:7]
        except Exception:
            return [topic]
