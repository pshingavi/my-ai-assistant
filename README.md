# Zizi Byte

**"Learn in bytes. Think in leaps."**

> Adaptive AI micro-learning platform that transforms dense course materials into
> personalized, bite-sized learning experiences — powered by RAG, Knowledge Graph traversal,
> Cohere reranking, and analogy-driven explanations.
>
> Named after Ziva — because learning should feel like play, not like work.

Built as the AIE9 Certification Challenge submission.

---

## The Problem It Solves

Dense technical courses (PDFs, notebooks, code) are hard to retain and connect across modules. Learners struggle to:

1. **Retain** concepts across sessions (each 50-200 slides + notebooks)
2. **Connect** ideas from earlier modules to later ones (e.g., Module 02 embeddings → Module 11 reranking)
3. **Apply** abstract concepts to their own professional context

**Zizi Byte's answer:** RAG retrieval over the actual course knowledge base + analogy-driven explanations personalized to the learner's question. Ask "explain embeddings" as a chef and get a recipe analogy. Ask it as an engineer and get a vector space analogy. The system grounds every answer in the course material — and never fabricates.

---

## What It Does

**Two modes, one chat interface:**

| Type | Trigger | What happens |
|------|---------|-------------|
| **Learn / Chat** | Any question | KG+Dense (k=15) → Cohere Rerank → analogy-driven grounded answer |
| **Content** | `create`, `trending`, `write post` | Research → dedup → RAG → LinkedIn post + HD poster image |
| **KG View** | `kg`, `graph`, `learning path` | Interactive Plotly knowledge graph of all topics |

---

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Docker — for Qdrant

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Required: OPENAI_API_KEY, TAVILY_API_KEY
# Optional: LANGCHAIN_API_KEY (LangSmith tracing), X_BEARER_TOKEN (X.com search)
# Optional: COHERE_API_KEY (Cohere Rerank — free tier at dashboard.cohere.com/api-keys)

# 3. Start Qdrant vector database
docker compose up -d

# 4. Ingest course materials + build knowledge graph
uv run python scripts/ingest_courses.py

# 5. Run the app
uv run chainlit run app.py
# → http://localhost:8000
```

---

## Features

### Adaptive Learning Chat

```
question → KG+Dense retrieval (k=15 candidates)
         → Cohere Rerank (top 5)
         → Analogy-first generation
             1. Vivid analogy (makes the concept click)
             2. Technical explanation (grounded in course material)
             3. Why it matters (practical implication)
             4. Follow-up question (deepens learning)
         → Sources list (file + relevance score)
```

- **Multi-hop Knowledge Graph**: embeds query → finds nearest topic nodes in NetworkX graph → traverses edges (up to 2 hops) → Dense retrieval on original query + related topics
- **Cohere Rerank**: `CohereRerank(model="rerank-v3.5")` reranks the 15-candidate pool to the top 5 most relevant chunks. Skips gracefully if `COHERE_API_KEY` not set.
- **Strictly grounded**: every claim cited by source file. Low-relevance chunks flagged explicitly rather than hallucinated over.

### Content Creation Pipeline

```
create → research (Tavily + X.com)
       → merge_topics (LLM selects hottest topic)
       → dedup_check   ← agentic decision point
           ↓ duplicate       ↓ new
         inform user    retrieve_context (Dense)
                        → generate_post (Hook→Analogy→Tech→CTA)
                        → generate_image (DALL-E 3 HD)
                        → ingest (Qdrant + Knowledge Graph)
                        → show sources (Tavily + X.com citations)
```

- **Deduplication**: cosine similarity against stored posts — stops if similarity > 0.85 and suggests a fresh angle
- **Post structure**: Hook → Analogy → Technical concept (KB-grounded) → CTA + hashtags
- **Source citations**: Tavily URLs and X.com links shown after every post

### Knowledge Graph View

Type `kg` to see an interactive Plotly network graph:

- **Purple circles** — course modules (8 topics, BUILDS_ON edges)
- **Blue diamonds** — generated LinkedIn posts (added automatically after `create`)
- Hover any node for description + related concepts

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                Zizi Byte  (app.py / Chainlit)            │
│  question → Learning Chat                                │
│  "create" → Content Pipeline                            │
│  "kg"     → KG Visualization (Plotly)                   │
└──────────────┬─────────────────────┬─────────────────────┘
               │                     │
   ┌───────────▼──────────┐  ┌───────▼───────────────────────────┐
   │  Content Pipeline    │  │  Learning Chat                     │
   │  (LangGraph)         │  │                                    │
   │  research            │  │  1. KG+Dense retrieval (k=15)      │
   │  merge_topics        │  │     KGRetriever (multi-hop)        │
   │  dedup_check ←──────│  │     + DenseRetriever (raw query)   │
   │  [AGENTIC DECISION] │  │                                    │
   │  retrieve_context   │  │  2. Cohere Rerank → top 5          │
   │  generate_post      │  │                                    │
   │  generate_image     │  │  3. Analogy-first generation       │
   │  ingest_post        │  │  4. Sources list                   │
   └─────────────────────┘  └────────────────────────────────────┘
               │
   ┌───────────▼──────────────────────────────────────────┐
   │  Shared Infrastructure                               │
   │  Qdrant (course_knowledge_base + generated_posts)    │
   │  NetworkX Topic Graph  (data/topic_graph.json)       │
   │  LangSmith tracing (optional, auto-on when key set)  │
   └──────────────────────────────────────────────────────┘
```

### Retrieval Stack

| Retriever | When used | How |
|-----------|-----------|-----|
| `KGRetriever` | Chat (primary) | Embed query → cosine-match topic nodes → traverse edges → Dense on each related topic |
| `DenseRetriever` | Chat (parallel) + Content pipeline | Embed raw query → Qdrant cosine search |
| `RerankRetriever` | Chat (post-retrieval) | Cohere rerank-v3.5 on 15-candidate pool → top 5 |
| `HyDERetriever` | Standalone eval only (Task 6) | Generate hypothetical doc → embed → Qdrant |
| `BM25Retriever` | Module 11 eval only | Sparse keyword index from Qdrant scroll |
| `MultiQueryRetriever` | Module 11 eval only | LLM generates 3 query variants |
| `EnsembleRetriever` | Module 11 eval only | RRF fusion of BM25 + Dense |
| `ParentDocRetriever` | Module 11 eval only | Child chunks retrieved, parent chunks returned |
| `SemanticChunkingRetriever` | Module 11 eval only | SemanticChunker(percentile) + Dense |

### Stack

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | GPT-4o-mini | Best cost/quality for analogy generation + streaming |
| Image | DALL-E 3 HD | Cinematic poster quality for content creation |
| Agent orchestration | LangGraph | Native conditional edges for agentic dedup decision |
| Embedding | text-embedding-3-small | Cost-efficient, 1536-dim |
| Vector DB | Qdrant (Docker) | Free local, metadata filtering, production-ready |
| Knowledge Graph | NetworkX + JSON | Lightweight multi-hop traversal, no extra infra |
| Reranking | Cohere rerank-v3.5 | Best faithfulness in Module 11 eval; free tier available |
| Search | Tavily + X.com (tweepy v2) | Real-time web + social trend coverage |
| Monitoring | LangSmith | Native LangGraph tracing, auto-enables when key is set |
| UI | Chainlit 2.x | Chat-native, streaming, Plotly elements, Steps accordion |
| Package manager | uv | Fast installs, workspace support |

---

## Knowledge Base

**Sources ingested** (20 files, 1,197 chunks across 8 modules):

| Module | Content |
|--------|---------|
| 02 Dense Vector Retrieval | Qdrant, embeddings, cosine similarity |
| 03 The Agent Loop | ReAct pattern, tool calling, LangGraph |
| 04 Agentic RAG | RAG pipeline, chunking, LangGraph |
| 05 Multi-Agent with LangGraph | LangGraph, state machines, supervisor patterns |
| 06 Agent Memory | Episodic + vector memory, Qdrant |
| 09 Synthetic Data + LangSmith | Tracing, evaluation datasets |
| 10 Evaluating RAG with RAGAS | Faithfulness, context recall, RAGAS |
| 11 Advanced Retrieval | BM25, reranking, multi-query, semantic chunking |

**Chunking strategy:**
- **PDFs**: `RecursiveCharacterTextSplitter` (512 chars, 50 overlap)
- **Notebooks**: cell-level pairing — each markdown cell paired with the following code cell
- **Markdown**: fixed-size (512 chars, 50 overlap)

To rebuild the KB from scratch:
```bash
uv run python scripts/reingest_fresh.py
```

---

## Evaluation

Full results and analysis: [`evals/EVALUATION_REPORT.md`](evals/EVALUATION_REPORT.md)

```bash
# Generate 15 synthetic Q&A pairs from the KB
uv run python evals/synthetic_data_gen.py --size 15

# Task 5 — Baseline: dense vector retrieval
uv run python evals/ragas_baseline.py --delay 1.0

# Task 6 — HyDE: advanced retrieval + comparison
uv run python evals/ragas_hyde.py --delay 1.0

# Task 6+ — KG+Dense multi-hop
uv run python evals/ragas_kg.py --delay 1.0

# Module 11 — All 7 strategies
uv run python evals/ragas_module11.py --delay 1.5

# Ablation — retriever × k grid
uv run python evals/ragas_ablation.py --delay 1.0
```

### Key Results (Module 11 full comparison)

| Strategy | Context Recall | Faithfulness | Answer Relevancy | Composite |
|---|---|---|---|---|
| **Semantic Chunking** | **0.629** | **0.661** | **0.972** | **2.261** |
| Naive Dense | 0.618 | 0.653 | 0.966 | 2.237 |
| HyDE | 0.634 | 0.477 | 0.520 | 1.631 |
| Ensemble (BM25+Dense) | 0.472 | 0.431 | 0.576 | 1.480 |
| Cohere Rerank | 0.422 | 0.467 | 0.516 | 1.405 |
| Multi-Query | 0.444 | 0.413 | 0.520 | 1.377 |
| Parent-Document | 0.459 | 0.398 | 0.449 | 1.307 |
| BM25 | 0.290 | 0.379 | 0.513 | 1.182 |

> KG+Dense scores 0.822 composite on RAGAS (which rewards focused single-question recall), but excels at multi-hop breadth for exploratory learning questions — retained in the chat pipeline for its pedagogical value.

---

## Configuration

All settings via `.env` (copy from `.env.example`):

```bash
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Optional — enables LangSmith tracing
LANGCHAIN_API_KEY=lsv2_...

# Optional — enables X.com media search
X_BEARER_TOKEN=AAAA...

# Optional — enables Cohere Rerank in chat (free tier available)
COHERE_API_KEY=...

# Image generation
IMAGE_MODEL=dall-e-3
IMAGE_QUALITY=hd

# Tuning
LLM_MODEL=gpt-4o-mini
DEDUP_THRESHOLD=0.85
RELEVANCE_THRESHOLD=0.50
CONTENT_DOMAIN=Generative AI
```

---

## Project Structure

```
zizi-byte/  (my-ai-assistant/)
├── app.py                        # Chainlit entry point — intent routing, UI
├── pyproject.toml                # uv project + all dependencies
├── docker-compose.yml            # Qdrant local container
├── evals/
│   ├── EVALUATION_REPORT.md      # Full certification challenge deliverables
│   ├── synthetic_data_gen.py     # RAGAS TestsetGenerator
│   ├── ragas_baseline.py         # Task 5 — Dense retrieval baseline
│   ├── ragas_hyde.py             # Task 6 — HyDE evaluation + comparison
│   ├── ragas_kg.py               # Task 6+ — KG+Dense multi-hop evaluation
│   ├── ragas_module11.py         # Module 11 — all 7 strategies
│   ├── ragas_ablation.py         # Retriever × k ablation study
│   ├── data/testset.json         # 15-sample synthetic golden dataset
│   └── results/                  # JSON result files for each strategy
├── scripts/
│   ├── ingest_courses.py         # Bulk ingest + course KG node/edge builder
│   └── reingest_fresh.py         # Clear + rebuild KB from scratch
└── src/
    ├── config.py                 # Pydantic Settings — single source of truth
    ├── llm.py                    # OpenAI client factory (lru_cache)
    ├── agents/
    │   ├── state.py              # ContentState + ChatState TypedDicts
    │   ├── content_pipeline.py   # LangGraph content creation graph
    │   └── chat_pipeline.py      # LangGraph KG RAG learning chat graph
    ├── tools/
    │   ├── tavily_tool.py        # Trending topic search
    │   ├── x_tool.py             # X.com tweet + media search
    │   ├── image_tool.py         # DALL-E 3 HD poster generation
    │   └── kg_viz_tool.py        # Plotly knowledge graph visualization
    ├── retrieval/
    │   ├── base.py               # Retriever protocol
    │   ├── dense_retriever.py    # Baseline — embed query → Qdrant
    │   ├── hyde_retriever.py     # HyDE — hypothetical doc → embed → Qdrant (eval only)
    │   ├── kg_retriever.py       # KG traversal + Dense multi-hop (production)
    │   ├── bm25_retriever.py     # BM25 sparse keyword (Module 11 eval)
    │   ├── multi_query_retriever.py  # MultiQueryRetriever (Module 11 eval)
    │   ├── rerank_retriever.py   # Cohere Rerank v3.5 (Module 11 eval + production)
    │   ├── ensemble_retriever.py # BM25+Dense RRF (Module 11 eval)
    │   ├── parent_doc_retriever.py   # ParentDocumentRetriever (Module 11 eval)
    │   └── semantic_chunking_retriever.py  # SemanticChunker (Module 11 eval)
    ├── memory/
    │   ├── qdrant_store.py       # Qdrant upsert/search + LangChain retriever
    │   └── topic_graph.py        # NetworkX KG — nodes, edges, traversal, JSON persistence
    └── ingestion/
        ├── course_ingester.py    # PDF + notebook + markdown loaders
        └── post_ingester.py      # Store posts + update KG with media metadata
```
