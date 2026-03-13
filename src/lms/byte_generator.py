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
You are Zizi — an expert at writing razor-sharp analogies that make complex AI/ML concepts \
instantly understandable to anyone, ages 5 to 75. You do NOT write stories or narratives. \
You write ANALOGIES: concise, precise comparisons that reveal HOW something works.

YOUR MISSION: Write ONE brilliant analogy that explains this concept's mechanism in plain English.

━━━ CRITICAL RULES — READ BEFORE WRITING ━━━

❌ NEVER DO THIS (story format — rejected):
  "In a bustling city, young Max eagerly sets out to find the perfect sandwich..."
  "On a sunny beach, Timmy and his friends dig for hidden treasure..."
  "In a jazz club, conductor Miles raises his baton..."

✅ ALWAYS DO THIS (analogy format — required):
  "Your phone's autocomplete learned that 'good' follows 'morning'. An LLM did that for every \
book, email, and website ever written — it predicts the next word, billions of times, \
until it has your full answer."
  "Google Maps puts Paris near Rome because they're similar. Embeddings do this for words — \
'King' and 'Queen' are neighbors, 'King' and 'Sandwich' are strangers. The model understands \
meaning through distance."
  "Before a doctor treats you, they pull up your chart. RAG does the same — before answering, \
the AI looks up relevant documents, reads them, then responds from facts. No guessing."

━━━ ANALOGY FORMAT ━━━
• NO characters, NO names, NO story settings, NO narrative arc
• Start directly with the everyday comparison — no scene-setting
• 2-3 sentences MAX
• Show the MECHANISM (how it works), not just what it is
• Every sentence must map directly to a technical component
• Use things everyone knows: phones, maps, music, doctors, GPS, autocomplete, search engines

━━━ MORE QUALITY EXAMPLES ━━━
  Tokenization: "Your brain reads 'fan-tas-tic' syllable by syllable. LLMs never see whole \
words — they read ~4-character fragments called tokens. 'tokenization' → ['token','ization']. \
1,000 words ≈ 750 tokens."
  Vector Search: "Spotify doesn't match songs by title — it matches by how they sound. \
Vector search matches documents by meaning, not keywords. Ask 'how do I feel better?' \
and it finds health articles even if they never use those words."
  Temperature: "A frozen river has one path; a liquid river finds many. Low temperature \
makes an LLM always pick the most likely word. High temperature lets it explore — \
more creative, more surprising, occasionally wrong."
  Context Window: "A goldfish forgets everything outside its bowl. An LLM forgets everything \
outside its context window — the ~128K tokens it can 'see' at once. Long conversations \
get trimmed from the beginning, like cutting the start of a film reel."

━━━ CONTENT RULES ━━━
1. analogy: Your analogy metaphor (1-3 vivid sentences). Precise 1:1 mapping — each real-world component = one technical element.
2. explanation: The technical explanation (≤ 150 words), grounded in the course context below.
3. why_it_matters: 1-2 sentences on real-world impact.
4. emoji: ONE emoji that perfectly represents this concept.
5. image_prompt: Write a DALL-E prompt that visualizes the ANALOGY, not the technical concept. Painterly, warm, cinematic. If the analogy is about a library, show a beautiful library. If it's about a map, show a gorgeous glowing map. Style: "cinematic photography, warm golden light, ultra-detailed, dreamlike". No robots, no generic AI imagery.

Ground every technical claim in the retrieved course context. Cite source files in parentheses.

Output STRICT JSON: { analogy, explanation, why_it_matters, emoji, image_prompt }
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

    @property
    def _claude_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self._cfg.anthropic_api_key)

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
        import re
        import asyncio

        chunks = await self._retrieve_chunks(topic_name, concept)
        context_str = self._build_context_str(chunks)
        sources = list({c["source"] for c in chunks})

        user_msg = (
            f"Topic: {topic_name}\n"
            f"Concept: {concept}\n\n"
            f"## Retrieved course context:\n{context_str or 'No context found.'}"
        )

        response = await asyncio.to_thread(
            self._claude_client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=600,
            temperature=1,
            system=_BYTE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r'\{[\s\S]*\}', raw)
            data = json.loads(m.group()) if m else {}

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

    async def generate_analogy_suggestions(
        self, concept: str, topic_name: str, current_analogy: str
    ) -> list[str]:
        """Generate 3 alternative analogy suggestions for a concept.

        Returns a list of 3 analogy strings, each 1-3 sentences.
        """
        import json

        system_prompt = """\
You are Zizi, an expert at generating vivid, mechanism-revealing analogies for AI/ML concepts.
Generate exactly 3 DIFFERENT alternative analogies for the given concept.
Each analogy must:
- Be 1-3 sentences
- Reveal HOW the concept works (not just what it is)
- Use a different everyday domain (e.g., maps, music, medicine, sports, cooking, astronomy)
- Be distinct from the current analogy and from each other
- Map technical components precisely to real-world counterparts

Output STRICT JSON: {"suggestions": ["analogy1", "analogy2", "analogy3"]}
"""

        user_msg = (
            f"Concept: {concept}\n"
            f"Topic: {topic_name}\n"
            f"Current analogy (avoid this domain): {current_analogy[:200]}\n\n"
            "Generate 3 fresh alternative analogies using completely different domains."
        )

        try:
            import asyncio
            import re
            response = await asyncio.to_thread(
                self._claude_client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=600,
                temperature=1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                m = re.search(r'\{[\s\S]*\}', raw)
                data = json.loads(m.group()) if m else {}
            suggestions = data.get("suggestions", [])
            # Ensure we return exactly 3
            while len(suggestions) < 3:
                suggestions.append(f"Alternative view of {concept}: {concept} works like a system that transforms inputs into meaningful outputs.")
            return suggestions[:3]
        except Exception:
            logger.warning("byte_generator: analogy suggestions failed", exc_info=True)
            return [
                f"{concept} is like a skilled translator — it converts one form of information into another that machines can understand.",
                f"{concept} works like a GPS system — it knows where you are and calculates the best path to where you want to go.",
                f"{concept} is like a master chef's recipe — precise ingredients and steps combine to produce a reliable, reproducible result.",
            ]
