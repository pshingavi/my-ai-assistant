# D2 Architecture Diagram

Zizi Byte architecture diagram built with [D2](https://d2lang.com/) — a declarative diagramming language that turns text into diagrams.

## What's Included

The diagram (`zizi-byte-architecture.d2`) shows:

1. **Data Ingestion Pipeline** — Course materials (PDF, notebooks, markdown) → Chunker → Embedder → Qdrant
2. **Learning Experience (UI)** — Next.js LMS :3000, Chainlit :8000
3. **API Layer** — FastAPI Bridge :8001
4. **Agentic Backend** — Named agents:
   - **Content Pipeline Agents**: Research, Merge, Dedup, RAG, Post Generator, Image, Ingest
   - **Chat Pipeline Agents**: KG Retriever, Dense Retriever, Rerank, Answer
   - **Byte Pipeline Agents**: Cache Check, Analogy Generator, Media, Persist
5. **AI Services & Tools** — OpenAI, Cohere, Tavily, X.com
6. **Storage & Cache** — Qdrant (vector store), Topic Graph (NetworkX), SQLite (analogies, p5_sketches, warm_jobs)

All data-flow arrows use `style.animated: true` for animated rendering when exported to SVG.

## Install D2 CLI

```bash
# macOS (Homebrew) — recommended
brew install d2

# Linux / macOS — official install script
curl -fsSL https://d2lang.com/install.sh | sh

# Or download from: https://github.com/terrastruct/d2/releases
```

## Build the Diagram

```bash
# From project root
cd docs

# Generate static SVG (default: dagre layout)
d2 zizi-byte-architecture.d2 zizi-byte-architecture.svg

# With TALA layout (if installed: brew install tala)
d2 zizi-byte-architecture.d2 zizi-byte-architecture.svg --layout=tala

# Generate animated SVG (flow animation on arrows)
d2 zizi-byte-architecture.d2 zizi-byte-architecture.svg --animate-interval=1200

# Generate PNG instead
d2 zizi-byte-architecture.d2 zizi-byte-architecture.png
```

## Layout Engines

- **dagre** — Default, hierarchical (always available)
- **elk** — Eclipse Layout Kernel
- **tala** — D2's custom engine, supports per-container directions (install separately)
