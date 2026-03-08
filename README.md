# AI Content Creator

> An agentic RAG application that researches trending AI topics, generates story-driven LinkedIn posts grounded in course material, and answers AI/ML questions with analogy-driven explanations — built for the AIE9 Certification Challenge.

---

## What It Does

**Two modes, one chat interface:**

| Type | Trigger | What happens |
|------|---------|-------------|
| **Content** | `create`, `trending`, `write post` | Research → dedup → RAG → LinkedIn post + HD poster image |
| **Chat** | Any question | KG+Dense retrieval → Cohere Rerank → grounded analogy-driven answer |
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
         inform user    retrieve_context (Dense)
                        → generate_post (Hook→Analogy→Tech→CTA)
                        → generate_image (DALL-E 3 HD, vivid style)
                        → ingest (Qdrant + Knowledge Graph)
                        → show sources (Tavily + X.com citations)
```

- **Trending research**: Tavily targets arxiv, OpenAI, DeepMind, HuggingFace, VentureBeat with the current month/year. X.com pulls high-engagement tweets with full media (images, video previews).
- **Deduplication**: cosine similarity against `posts_collection` — if similarity > 0.85 the pipeline stops and suggests a fresh angle.
- **Post structure**: Hook (challenge an assumption) → Analogy (vivid scene) → Tech concept (grounded in course KB) → CTA (question or reshare ask + hashtags).
- **Images**: DALL-E 3 `quality=hd`, `style=vivid` — cinematic neon-noir with photorealistic visual metaphors.
- **Source citations**: every post shows all Tavily URLs and X.com tweet links as collapsible references.

### Knowledge Chat

- **KG + Dense retrieval**: embeds query → finds nearest topic nodes in NetworkX graph → traverses edges (up to 2 hops) → runs Dense retrieval on original query + related topics. Simultaneously runs a direct dense search on the raw query to guarantee the most obvious matches are in the candidate pool (k=15 candidates total).
- **Cohere Rerank**: `CohereRerank(model="rerank-v3.5")` reranks the 15-candidate pool to the top 5 most relevant chunks. Requires `COHERE_API_KEY`; skips gracefully if absent.
- **Grounded answers**: system prompt enforces inline citations by source file name with analogy-first structure: Analogy → Technical explanation → Why it matters → Follow-up question.
- **Sources always shown**: compact list of source filenames with relevance scores below every answer.

### Knowledge Graph View

Type `kg` to see an interactive Plotly network graph:

- **Purple circles** — AIE9 bootcamp course modules (8 topics pre-wired with BUILDS_ON edges)
- **Blue diamonds** — generated LinkedIn posts (added automatically after each `create` run)
- Hover any node for description + related concepts
- Grows automatically: add new course material via `ingest_courses.py`, new post topics via `create`

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
   ┌───────────▼──────────┐  ┌────────▼──────────────────────────┐
   │  Content Pipeline    │  │  Chat Pipeline                     │
   │  (LangGraph)         │  │  (app.py inline)                   │
   │                      │  │                                    │
   │  research_node        │  │  1. KG+Dense retrieval (k=15)      │
   │  merge_topics_node    │  │     KGRetriever (multi-hop)        │
   │  dedup_check_node ←  │  │     + DenseRetriever (raw query)   │
   │  [AGENTIC DECISION]  │  │                                    │
   │  retrieve_context    │  │  2. Cohere Rerank → top 5          │
   │  generate_post       │  │                                    │
   │  generate_image      │  │  3. Stream answer (cited)          │
   │  ingest_post         │  │  4. Sources list                   │
   └──────────────────────┘  └────────────────────────────────────┘
               │
   ┌───────────▼──────────────────────────────────────────┐
   │  Shared Infrastructure                               │
   │  Qdrant (course_knowledge_base + generated_posts)    │
   │  NetworkX Topic Graph  (data/topic_graph.json)       │
   │  LangSmith tracing (optional, auto-on when key set)  │
   └───────────────────────────────────────────────────────┘
```

### Retrieval Stack

| Retriever | When used | How |
|-----------|-----------|-----|
| `KGRetriever` | Chat (primary) | Embed query → cosine-match topic nodes → traverse edges → Dense on each related topic |
| `DenseRetriever` | Chat (parallel with KG) | Embed raw query → Qdrant cosine search |
| `RerankRetriever` | Chat (post-retrieval) | Cohere rerank-v3.5 on 15-candidate pool → top 5 |
| `HyDERetriever` | Standalone eval only | Generate hypothetical doc → embed → Qdrant (Task 6 evaluation) |
| `BM25Retriever` | Module 11 eval only | Sparse keyword index from Qdrant scroll |
| `MultiQueryRetriever` | Module 11 eval only | LLM generates 3 query variants |
| `EnsembleRetriever` | Module 11 eval only | RRF fusion of BM25 + Dense |
| `ParentDocRetriever` | Module 11 eval only | Child chunks retrieved, parent chunks returned |
| `SemanticChunkingRetriever` | Module 11 eval only | SemanticChunker(percentile) + Dense |

### Stack

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | GPT-4o-mini | Best cost/quality for JSON output + streaming |
| Image | DALL-E 3 HD | Cinematic poster quality |
| Agent orchestration | LangGraph | Native conditional edges for agentic dedup decision |
| Embedding | text-embedding-3-small | Cost-efficient, 1536-dim |
| Vector DB | Qdrant (Docker) | Free local, metadata filtering, production-ready |
| KG | NetworkX + JSON | Lightweight graph traversal, no extra infra |
| Reranking | Cohere rerank-v3.5 | Best faithfulness in Module 11 eval; free tier available |
| Search | Tavily + X.com (tweepy v2) | Real-time web + social trend coverage |
| Monitoring | LangSmith | Native LangGraph tracing, auto-enables when key is set |
| UI | Chainlit 2.x | Chat-native, streaming, Plotly elements, Steps accordion |
| Package manager | uv | Fast installs, workspace support |

---

## Knowledge Base

**Sources ingested** (20 files, 1,197 chunks):

| Module | Content | Format |
|--------|---------|--------|
| 02 Dense Vector Retrieval | Qdrant, embeddings, cosine similarity | PDF + notebook |
| 03 The Agent Loop | ReAct pattern, tool calling, LangGraph | PDF + notebook |
| 04 Agentic RAG | RAG pipeline, chunking, LangGraph | PDF + notebook |
| 05 Multi-Agent with LangGraph | LangGraph, state machines, supervisor | PDF + notebook |
| 06 Agent Memory | Episodic + vector memory, Qdrant | PDF + notebook |
| 09 Synthetic Data + LangSmith | Tracing, evaluation datasets | PDF + notebook |
| 10 Evaluating RAG with RAGAS | Faithfulness, context recall, RAGAS | PDF + notebook |
| 11 Advanced Retrieval | BM25, reranking, multi-query, semantic chunking | PDF + notebook |

**Chunking strategy:**
- **PDFs**: `RecursiveCharacterTextSplitter` (512 chars, 50 overlap)
- **Notebooks**: cell-level pairing — each markdown cell paired with the following code cell
- **Markdown**: fixed-size (512 chars, 50 overlap)

To add new cohort material: drop modules into `../Learn-AI-Engineering/`, add entries to `_MODULE_TOPICS` and `_MODULE_RELATIONS` in `scripts/ingest_courses.py`, then re-run:
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

# Task 6 — Advanced: HyDE retrieval + comparison
uv run python evals/ragas_hyde.py --delay 1.0

# Task 6+ — KG+Dense multi-hop evaluation
uv run python evals/ragas_kg.py --delay 1.0

# Module 11 — All 7 strategies (BM25, MultiQuery, ParentDoc, Rerank, Ensemble, SemanticChunking)
uv run python evals/ragas_module11.py --delay 1.5
uv run python evals/ragas_module11.py --only rerank --delay 2.0  # Cohere only

# Ablation — retriever × k grid search
uv run python evals/ragas_ablation.py --delay 1.0
```

### Key Results

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
| KG+Dense | 0.339 | 0.222 | 0.261 | 0.822 |

> KG+Dense scores low on RAGAS (which rewards focused single-question recall) but excels at multi-hop breadth for exploratory learning questions — retained in the chat pipeline for this reason.

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

# Optional — enables Cohere Rerank in chat pipeline (free tier available)
COHERE_API_KEY=...

# Image generation (dall-e-3 default)
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
├── evals/
│   ├── EVALUATION_REPORT.md      # Full certification challenge deliverables document
│   ├── synthetic_data_gen.py     # RAGAS TestsetGenerator
│   ├── ragas_baseline.py         # Task 5 — Dense retrieval baseline
│   ├── ragas_hyde.py             # Task 6 — HyDE evaluation + comparison table
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
    │   └── chat_pipeline.py      # LangGraph KG RAG chat graph
    ├── tools/
    │   ├── tavily_tool.py        # Trending topic search (news-focused)
    │   ├── x_tool.py             # X.com tweet + media search (tweepy v2)
    │   ├── image_tool.py         # DALL-E 3 HD poster generation
    │   └── kg_viz_tool.py        # Plotly knowledge graph visualization
    ├── retrieval/
    │   ├── base.py               # Retriever protocol
    │   ├── dense_retriever.py    # Baseline — embed query → Qdrant
    │   ├── hyde_retriever.py     # HyDE — hypothetical doc → embed → Qdrant
    │   ├── kg_retriever.py       # KG traversal + Dense multi-hop (chat pipeline)
    │   ├── bm25_retriever.py     # BM25 sparse keyword (Module 11)
    │   ├── multi_query_retriever.py  # MultiQueryRetriever (Module 11)
    │   ├── rerank_retriever.py   # Cohere Rerank v3.5 (Module 11 + chat)
    │   ├── ensemble_retriever.py # BM25+Dense RRF (Module 11)
    │   ├── parent_doc_retriever.py   # ParentDocumentRetriever (Module 11)
    │   └── semantic_chunking_retriever.py  # SemanticChunker (Module 11)
    ├── memory/
    │   ├── qdrant_store.py       # Qdrant upsert/search + LangChain retriever
    │   └── topic_graph.py        # NetworkX KG — nodes, edges, traversal, JSON persistence
    └── ingestion/
        ├── course_ingester.py    # PDF + notebook + markdown loaders
        └── post_ingester.py      # Store posts + update KG with media metadata
```
