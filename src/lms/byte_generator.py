"""Byte generator — produces analogy-first byte-sized learning content.

Each "byte" covers ONE concept from a topic and consists of:
  - A vivid analogy grounded in everyday life
  - A concise technical explanation (grounded in KB chunks)
  - Why it matters
  - A short code snippet (Build mode) extracted from course notebooks
  - Source citations
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class ByteContent:
    concept: str
    topic_name: str
    analogy: str
    explanation: str
    why_it_matters: str
    emoji: str
    sources: list[str] = field(default_factory=list)
    image_prompt: str = ""  # DALL-E prompt for the analogy illustration


@dataclass
class BuildContent:
    concept: str
    topic_name: str
    code_snippet: str
    language: str
    explanation: str
    run_notes: str  # what to expect when running this code
    sources: list[str] = field(default_factory=list)


_BYTE_SYSTEM = """\
You are Zizi, an expert AI educator. Your job is to explain ONE concept in a byte-sized, \
analogy-first format that can be understood in under 2 minutes.

RULES:
1. Start with a single vivid analogy from everyday life (cooking, sports, music, etc.).
2. Then explain the technical concept concisely (≤ 150 words).
3. End with "Why it matters" (1–2 sentences).
4. Ground every claim in the retrieved course context — cite source files in parentheses.
5. Never fabricate facts. If context is sparse, say so.
6. Pick ONE emoji that captures the concept (for the byte card header).

Output STRICT JSON with keys:
  analogy (string), explanation (string), why_it_matters (string), emoji (string), image_prompt (string)

The image_prompt should be a vivid DALL-E prompt (≤ 80 words) describing an illustration \
of the analogy — no text in the image, photorealistic or artistic style.
"""

_BUILD_SYSTEM = """\
You are Zizi, an AI engineering educator. Extract the MOST illustrative code snippet for \
the concept from the retrieved course notebook context, then explain it line-by-line.

RULES:
1. Return the shortest self-contained runnable code that demonstrates the concept.
2. The explanation should walk through each meaningful line.
3. Include what the learner should expect to see when running it.
4. Cite the source notebook in parentheses.

Output STRICT JSON with keys:
  code_snippet (string), language (string), explanation (string), run_notes (string)
"""


class ByteGenerator:
    """Generates byte-sized learning content grounded in the KB."""

    def __init__(self) -> None:
        from src.config import get_settings
        from src.llm import get_async_openai
        self._cfg = get_settings()
        self._client = get_async_openai()

    async def _retrieve_chunks(self, topic_name: str, concept: str, k: int = 8) -> list[dict]:
        """Retrieve KB chunks relevant to this concept."""
        from src.retrieval.dense_retriever import DenseRetriever
        query = f"{topic_name}: {concept}"
        retriever = DenseRetriever()
        chunks = await retriever.retrieve(query, k=k)
        return [
            {
                "content": c.content if hasattr(c, "content") else c["content"],
                "source": c.source if hasattr(c, "source") else c["source"],
            }
            for c in chunks
        ]

    def _build_context_str(self, chunks: list[dict]) -> str:
        return "\n\n---\n\n".join(
            f"[Source: {c['source']}]\n{c['content']}" for c in chunks
        )

    async def generate_byte(self, topic_name: str, concept: str) -> ByteContent:
        """Generate a single analogy-first byte for one concept."""
        import json

        chunks = await self._retrieve_chunks(topic_name, concept)
        context_str = self._build_context_str(chunks)
        sources = list({c["source"] for c in chunks})

        user_msg = (
            f"Topic: {topic_name}\n"
            f"Concept: {concept}\n\n"
            f"## Retrieved course context:\n{context_str or 'No context found.'}"
        )

        resp = await self._client.chat.completions.create(
            model=self._cfg.llm_model,
            messages=[
                {"role": "system", "content": _BYTE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        return ByteContent(
            concept=concept,
            topic_name=topic_name,
            analogy=data.get("analogy", ""),
            explanation=data.get("explanation", ""),
            why_it_matters=data.get("why_it_matters", ""),
            emoji=data.get("emoji", "🧠"),
            image_prompt=data.get("image_prompt", ""),
            sources=sources,
        )

    async def generate_byte_stream(
        self, topic_name: str, concept: str
    ) -> AsyncIterator[str]:
        """Stream the byte as SSE-friendly text chunks."""
        chunks = await self._retrieve_chunks(topic_name, concept)
        context_str = self._build_context_str(chunks)

        user_msg = (
            f"Topic: {topic_name}\nConcept: {concept}\n\n"
            f"## Retrieved context:\n{context_str or 'No context found.'}"
        )

        stream = await self._client.chat.completions.create(
            model=self._cfg.llm_model,
            messages=[
                {"role": "system", "content": _BYTE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def generate_build(self, topic_name: str, concept: str) -> BuildContent:
        """Generate a code-first Build mode card for one concept."""
        import json

        chunks = await self._retrieve_chunks(topic_name, concept, k=10)
        # Filter to notebook chunks only for code examples
        nb_chunks = [c for c in chunks if ".ipynb" in c.get("source", "")]
        context_chunks = nb_chunks or chunks
        context_str = self._build_context_str(context_chunks)
        sources = list({c["source"] for c in context_chunks})

        user_msg = (
            f"Topic: {topic_name}\n"
            f"Concept: {concept}\n\n"
            f"## Retrieved notebook context:\n{context_str or 'No notebook context found.'}"
        )

        resp = await self._client.chat.completions.create(
            model=self._cfg.llm_model,
            messages=[
                {"role": "system", "content": _BUILD_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=700,
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        return BuildContent(
            concept=concept,
            topic_name=topic_name,
            code_snippet=data.get("code_snippet", "# No code example found"),
            language=data.get("language", "python"),
            explanation=data.get("explanation", ""),
            run_notes=data.get("run_notes", ""),
            sources=sources,
        )

    async def generate_all_bytes(
        self, topic_name: str, concepts: list[str]
    ) -> list[ByteContent]:
        """Generate bytes for all concepts in a topic (concurrently)."""
        tasks = [self.generate_byte(topic_name, c) for c in concepts]
        return await asyncio.gather(*tasks)
