# AI Content Creator

> An agentic RAG application that researches trending AI topics, generates story-driven LinkedIn posts grounded in course material, and answers AI/ML questions with a live knowledge graph — built for the AIE9 Certification Challenge.

---

## What It Does

**Two modes, one chat interface:**

| Type | Trigger | What happens |
|------|---------|-------------|
| **Content** | `create`, `trending`, `write post` | Research → dedup → RAG → LinkedIn post + HD poster image |
| **Chat** | Any question | KG traversal + HyDE retrieval → grounded analogy-driven answer |
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
# Fill in: OPENAI_API_KEY, TAVILY_API_KEY
# Optional: LANGCHAIN_API_KEY (LangSmith tracing), X_BEARER_TOKEN (X.com search)

# 3. Start Qdrant vector database
docker compose up -d

# 4. Ingest AIE9 course materials + build knowledge graph
uv run python scripts/ingest_courses.py

# 5. Run the app
uv run chainlit run app.py
# → http://localhost:8000
```

---

## Features

### Content Creation Pipeline

```
create → research (Tavily + X.com)
       → merge_topics (LLM selects hottest topic)
       → dedup_check   ← agentic decision point
           ↓ duplicate       ↓ new
         inform user    retrieve_context (HyDE)
                        → generate_post (Hook→Analogy→Tech→CTA)
                        → generate_image (DALL-E 3 HD, vivid style)
                        → ingest (Qdrant + Knowledge Graph)
                        → show sources (Tavily + X.com citations)
```

- **Trending research**: Tavily targets arxiv, OpenAI, DeepMind, HuggingFace, VentureBeat with the current month/year. X.com pulls high-engagement tweets with full media (images, video previews).
- **Deduplication**: cosine similarity against `posts_collection` — if similarity > 0.85 the pipeline stops and suggests a fresh angle.
- **Post structure**: Hook (challenge an assumption) → Analogy (vivid scene) → Tech concept (grounded in course KB) → CTA (question or reshare ask + hashtags).
- **Images**: DALL-E 3 `quality=hd`, `style=vivid` — cinematic neon-noir with photorealistic visual metaphors. Set `IMAGE_MODEL=gpt-image-1` in `.env` for higher quality if your API tier allows.
- **Source citations**: every post shows all Tavily URLs and X.com tweet links as collapsible references.

### Knowledge Chat

- **KG + HyDE retrieval**: embeds query → finds nearest topic nodes in NetworkX graph → traverses edges (up to 2 hops) → runs HyDE on each related topic for multi-hop context.
- **Automatic fallback**: if KG+HyDE score < 0.35 → merges with dense retrieval. If score < 0.25 → also searches Tavily web and adds web sources.
- **Grounded answers**: system prompt enforces inline citations by source file name. Low-confidence results are flagged explicitly.
- **Sources always shown**: never an answer without references — KB chunks with relevance scores, or web fallback, or honest "no material found" message.

### Knowledge Graph View

Type `kg` to see an interactive Plotly network graph:

- **Purple circles** — AIE9 bootcamp course modules (8 topics pre-wired with BUILDS_ON edges)
- **Blue diamonds** — generated LinkedIn posts (added automatically after each `create` run)
- Hover any node for description + related concepts
- Grows automatically: add new course cohort material via `ingest_courses.py`, new post topics via `create`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Chainlit UI  (app.py)                  │
│  "create" → Content Pipeline                            │
│  "kg"     → KG Visualization (Plotly)                   │
│  question → Chat Pipeline                               │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
   ┌───────────▼──────────┐  ┌────────▼──────────────────┐
   │  Content Pipeline    │  │  Chat Pipeline             │
   │  (LangGraph)         │  │  (LangGraph)               │
   │                      │  │                            │
   │  research_node        │  │  kg_retrieve_node          │
   │  merge_topics_node    │  │  (KGRetriever →            │
   │  dedup_check_node ←  │  │   HyDE → Qdrant)           │
   │  [AGENTIC DECISION]  │  │                            │
   │  retrieve_context    │  │  generate_answer_node      │
   │  generate_post       │  │  (streaming, cited)        │
   │  generate_image      │  └────────────────────────────┘
   │  ingest_post         │
   └──────────────────────┘
               │
   ┌───────────▼──────────────────────────────────────────┐
   │  Shared Infrastructure                               │
   │  Qdrant (course_knowledge_base + generated_posts)    │
   │  NetworkX Topic Graph  (data/topic_graph.json)        │
   │  LangSmith tracing (optional, auto-on when key set)  │
   └───────────────────────────────────────────────────────┘
```

### Retrieval Stack

| Retriever | When used | How |
|-----------|-----------|-----|
| `KGRetriever` | Chat (primary) | Embed query → cosine-match topic nodes → traverse edges → HyDE on each related topic |
| `HyDERetriever` | Content pipeline | Generate hypothetical document → embed → Qdrant search |
| `DenseRetriever` | Chat (fallback) | Embed raw query → Qdrant search |
| Tavily web | Chat (fallback) | Live web search when KB score < 0.25 |

### Stack

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | GPT-4o-mini (default) / GPT-4o | Best JSON output + streaming |
| Image | DALL-E 3 HD / gpt-image-1 | Cinematic poster quality |
| Agent orchestration | LangGraph | Native conditional edges for agentic dedup decision |
| Embedding | text-embedding-3-small | Cost-efficient, 1536-dim |
| Vector DB | Qdrant (Docker) | Free local, metadata filtering, production-ready |
| KG | NetworkX + JSON | Lightweight graph traversal, no extra infra |
| Search | Tavily + X.com (tweepy v2) | Real-time web + social trend coverage |
| Monitoring | LangSmith | Native LangGraph tracing, auto-enables when key is set |
| UI | Chainlit 2.x | Chat-native, streaming, Plotly elements, Steps accordion |
| Package manager | uv | Fast installs, workspace support |

---

## Knowledge Base

**Sources ingested** (8 AIE9 modules, 1,212 chunks):

| Module | Content | Format |
|--------|---------|--------|
| 02 Dense Vector Retrieval | Qdrant, embeddings, cosine similarity | PDF + notebook |
| 03 The Agent Loop | ReAct pattern, tool calling | PDF + notebook |
| 04 Agentic RAG From Scratch | RAG pipeline, chunking | PDF + notebook |
| 05 Multi-Agent with LangGraph | LangGraph, state machines | PDF + notebook |
| 06 Agent Memory | Episodic + vector memory | PDF + notebook |
| 09 Synthetic Data + LangSmith | Tracing, evaluation datasets | PDF + notebook |
| 10 Evaluating RAG with RAGAS | Faithfulness, context recall | PDF + notebook |
| 11 Advanced Retrieval | HyDE, reranking, multi-hop | PDF + notebook |

**Chunking strategy:**
- **PDFs**: `RecursiveCharacterTextSplitter` (512 tokens, 50 overlap)
- **Notebooks**: cell-level pairing — each markdown cell paired with the following code cell
- **Markdown**: fixed-size (512, 50 overlap)

To add new cohort material: drop modules into `../Learn-AI-Engineering/`, add entries to `_MODULE_TOPICS` and `_MODULE_RELATIONS` in `scripts/ingest_courses.py`, then re-run ingestion.

---

## Evaluation

```bash
# Generate 15 synthetic Q&A pairs from the KB
uv run python evals/synthetic_data_gen.py --size 15

# Baseline: dense vector retrieval
uv run python evals/ragas_baseline.py --delay 1.0

# Advanced: HyDE retrieval + comparison table
uv run python evals/ragas_hyde.py --delay 1.0
```

Results saved to `evals/results/`. The HyDE eval prints a side-by-side comparison table.

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

# Image generation (dall-e-3 default; gpt-image-1 for higher quality if available)
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
my-ai-assistant/
├── app.py                        # Chainlit entry point — intent routing, UI
├── pyproject.toml                # uv project + all dependencies
├── docker-compose.yml            # Qdrant local container
├── src/
│   ├── config.py                 # Pydantic Settings — single source of truth
│   ├── llm.py                    # OpenAI client factory (lru_cache)
│   ├── agents/
│   │   ├── state.py              # ContentState + ChatState TypedDicts
│   │   ├── content_pipeline.py   # LangGraph content creation graph
│   │   └── chat_pipeline.py      # LangGraph KG RAG chat graph
│   ├── tools/
│   │   ├── tavily_tool.py        # Trending topic search (news-focused)
│   │   ├── x_tool.py             # X.com tweet + media search (tweepy v2)
│   │   ├── image_tool.py         # DALL-E 3 HD / gpt-image-1 poster generation
│   │   └── kg_viz_tool.py        # Plotly knowledge graph visualization
│   ├── retrieval/
│   │   ├── base.py               # Retriever protocol
│   │   ├── dense_retriever.py    # Baseline — embed query → Qdrant
│   │   ├── hyde_retriever.py     # Advanced — hypothetical doc → embed → Qdrant
│   │   └── kg_retriever.py       # KG traversal + HyDE multi-hop
│   ├── memory/
│   │   ├── qdrant_store.py       # Qdrant upsert/search + LangChain retriever
│   │   └── topic_graph.py        # NetworkX KG — nodes, edges, traversal, JSON persistence
│   └── ingestion/
│       ├── course_ingester.py    # PDF + notebook + markdown loaders
│       └── post_ingester.py      # Store posts + update KG with media metadata
├── scripts/
│   └── ingest_courses.py         # Bulk ingest + course KG node/edge builder
└── evals/
    ├── synthetic_data_gen.py     # RAGAS TestsetGenerator
    ├── ragas_baseline.py         # Dense retrieval baseline
    └── ragas_hyde.py             # HyDE evaluation + comparison table
```
