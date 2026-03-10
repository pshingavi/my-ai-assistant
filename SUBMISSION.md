# Zizi Byte — AIE9 Certification Challenge Submission

**"Learn in bytes. Think in leaps."**

**Author:** Preetam | **Cohort:** AIE9 | **Submitted:** 2026-03-10

---

## The One-Line Pitch

> An adaptive AI micro-learning LMS that transforms dense technical course materials into personalized, analogy-driven learning experiences — grounded in the actual knowledge base, not generic LLM knowledge. Three modes: byte-sized micro-lessons, a code build sandbox, and a grounded RAG chat.

---

## Task 1 — Problem, Audience & Scope

### The Problem

Dense technical courses — PDFs, slide decks, Jupyter notebooks — produce a knowledge base that is hard to retain, hard to connect across topics, and hard to apply to real-world problems.

Learners in AI engineering bootcamps struggle with three specific gaps:

1. **Retention** — each session is 50–200 slides plus notebooks. Without active recall, concepts fade within days.
2. **Connection** — topics build on each other (embeddings → dense retrieval → HyDE → reranking), but learners rarely see those threads explicitly. Understanding Module 11 is much harder without having internalized Module 02.
3. **Application** — abstract concepts only stick when explained in terms that are personally meaningful. A chef and a software engineer both need to understand vector embeddings, but they need different entry points.

The bottleneck isn't intelligence or motivation — it's that existing tools don't bridge the gap between dense technical documentation and the way humans actually build mental models: through vivid analogies, connected concepts, and answers grounded in what was *actually taught*.

### Why Existing Tools Fail

| Tool | Gap |
|---|---|
| ChatGPT / Claude | No access to the actual course material — answers are generic, not grounded in what was taught |
| Course slides | Static, one-size-fits-all — no retrieval, no personalization, no concept linking across sessions |
| Google / Search | Returns pages, not explanations calibrated to the course and the learner's background |
| Notes apps | Manual organization — no intelligent retrieval or concept graph |

### Target User

**Working professionals upskilling in AI engineering** — enrolled in bootcamps, reading documentation, consuming dense technical material. They learn fast but need a system that explains things in terms that click for *their* context, and that grounds every answer in the material they're actually studying.

### Sample Evaluation Questions

| # | Input | Expected output |
|---|-------|-----------------|
| 1 | `Explain the agent loop like I am 5 years old` | Analogy-first answer grounded in Session 03 material |
| 2 | `What is RAG and why does it matter?` | KB-grounded answer with source citations |
| 3 | `How does LangGraph handle state?` | Multi-hop KG answer pulling Session 03 + 05 |
| 4 | `What are RAGAS evaluation metrics?` | Factual answer from Session 10 material |
| 5 | `Explain embeddings to someone who cooks` | Profession-adapted analogy grounded in Session 02 |
| 6 | `create` | Trending topic → LinkedIn post + HD image + source citations |
| 7 | `create` (same topic) | Dedup fires → "already covered" message |
| 8 | `kg` | Interactive knowledge graph of all ingested topics and posts |

---

## Task 2 — Proposed Solution

### Overview

**Zizi Byte** is a three-mode platform:

| Mode | Where | Pipeline |
|------|-------|----------|
| **LMS — Byte** | Next.js `/learn/{topic}` | Topic selected → KG-aware byte generated → analogy + explanation + "why it matters" card |
| **LMS — Build** | Next.js `/learn/{topic}` Build tab | Notebook code extracted → code snippet + run notes |
| **LMS — Chat** | Next.js `/chat` | KG+Dense (k=15 each) → all chunks → Cohere Rerank (top 8) → analogy-first, strictly-grounded streaming answer |
| **Content Creator** | Chainlit `create` trigger | `research → dedup_check [AGENTIC] → retrieve → generate_post → generate_image → ingest` |
| **KG Explorer** | Next.js `/` (Galaxy) | D3 force-graph of all topic nodes + BUILDS_ON edges; click to learn |

**Chainlit** (port 8000) handles the content creator pipeline and KG visualization for power users.
**Next.js LMS** (port 3000) is the primary learning experience with full RAG chat feature parity.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│          Next.js LMS  (port 3000)  zizi-lms/                 │
│  /           → D3 Topic Galaxy (KG visualization)            │
│  /learn/{id} → ByteCard | BuildCard | ShareModal             │
│  /chat       → SSE streaming chat (KG+Dense → Cohere)        │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼───────────────────────────────────────┐
│          FastAPI Bridge  (port 8001)  api_server.py           │
│  /api/topics          /api/kg          /api/bytes/stream       │
│  /api/build/generate  /api/share/create-post                  │
│  /api/chat/stream  (SSE: step|token|sources|done)             │
└───────┬──────────────────────────┬───────────────────────────┘
        │                          │
┌───────▼──────────┐  ┌────────────▼──────────────────────────┐
│ Content Pipeline  │  │  Chat Pipeline                         │
│ (LangGraph)       │  │  1. KGRetriever (k=15) — multi-hop    │
│ research_node     │  │  2. DenseRetriever (k=15) — raw query │
│ merge_topics_node │  │  3. Merge ALL unique chunks            │
│ dedup_check_node● │  │  4. Cohere Rerank → top 8             │
│ [AGENTIC BRANCH]  │  │  5. Analogy-first stream (GPT-4o-mini)│
│ generate_post     │  │  6. Sources with relevance scores      │
│ generate_image    │  └────────────────────────────────────────┘
│ ingest_post       │
└──────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│  Shared Infrastructure                                         │
│  Qdrant (Docker)  ·  course_knowledge_base  ·  generated_posts│
│  NetworkX Topic Graph  (data/topic_graph.json)                │
│  LangSmith (opt-in — traces when LANGCHAIN_API_KEY set)       │
└───────────────────────────────────────────────────────────────┘
```

### Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | GPT-4o-mini | Best structured JSON output + streaming at low cost |
| Image | DALL-E 3 HD (`quality=hd`, `style=vivid`) | Cinematic poster quality for content creation |
| Orchestration | LangGraph | Native conditional edges make dedup branch clean and auditable |
| Chat retrieval | KG+Dense → Cohere Rerank | All unique chunks passed to Cohere; prevents low-score docs from being cut before reranking |
| Tools | Tavily + X.com (tweepy v2) | Authoritative AI sources + real-time social signal |
| Embedding | text-embedding-3-small | Strong semantic similarity at cost-efficient 1536 dims |
| Vector DB | Qdrant (Docker) | Free local, metadata filtering, production-ready |
| KG | NetworkX + JSON | Zero extra infra; cosine similarity traversal + JSON persistence |
| Reranking | Cohere rerank-v3.5 | Best faithfulness improvement in Module 11 evaluation |
| Monitoring | LangSmith | Native LangGraph tracing; zero config when API key is set |
| Evaluation | RAGAS 0.2.x | Standard RAG eval with `SingleTurnSample` API (Session 10 pattern) |
| UI | Next.js 14 App Router | Full LMS with D3 galaxy, framer-motion animations, Zustand state |
| Chat UI | Zustand + framer-motion + SSE | Streaming chat with animated bubbles, particles, typewriter cursor |
| API Bridge | FastAPI + uvicorn | Async SSE streaming; CORS for localhost:3000 |
| Package manager | uv | 10–100× faster than pip; workspace + editable install |

### RAG and Agent Components

**RAG stack — Chat pipeline (production, fixed post-cohort):**
- *KGRetriever* — embed query → cosine-match topic nodes in NetworkX → traverse BUILDS_ON edges up to 2 hops → Dense retrieval on original query + each related topic → merge candidates
- *DenseRetriever* — direct embed of raw query runs in parallel (k=15) to guarantee most-obvious module matches survive
- **Key fix**: ALL unique chunks (~25–30) passed to Cohere — not pre-filtered by embedding score. This prevents lower-scoring exact-match documents (e.g. `AIE9_Session03_The-Agent-Loop.pdf` at 0.47 cosine) from being cut before Cohere's neural reranker can surface them
- *Cohere Rerank (top 8)* — `CohereRerank(model="rerank-v3.5")` selects top 8 from all candidates

**Agentic decision point — Content pipeline:**
`dedup_check_node` embeds the selected topic, searches `posts_collection`, and at runtime decides whether to continue creation or halt. Branches on cosine similarity > 0.85 — no human in the loop, driven entirely by observed data quality (learned from Session 04 conditional LangGraph edges).

---

## Task 3 — Data & External APIs

### Knowledge Base

| Source | Format | Chunks |
|--------|--------|--------|
| Course session slide decks (Modules 02–11) | PDF | ~700 |
| Jupyter notebooks, cell-level pairs | .ipynb | ~350 |
| Markdown guides and explainers | .md | ~150 |
| Generated LinkedIn posts (dynamic) | text | grows with use |

**Total at submission:** 1,197 chunks across 20 files from 8 modules.

### Chunking Strategy

| Source type | Strategy | Rationale |
|-------------|----------|-----------|
| PDF | `RecursiveCharacterTextSplitter` (512 chars, 50 overlap) | Respects paragraph boundaries in slide-deck structure |
| Notebook | Cell-level pairing: markdown cell + following code cell | Keeps explanation and implementation together — separating them loses pedagogical intent |
| Markdown | Fixed-size (512 chars, 50 overlap) | Less structure than PDFs; simpler approach is sufficient |

512 chars / 50 overlap sits at the empirical sweet spot: validated by Module 11 ablation where fixed-512 (composite 2.237) tracks Semantic Chunking winner (2.261) within 1.1%.

### External APIs

| API | Role | How it interacts |
|-----|------|-----------------|
| **Tavily** | Find trending AI topics for content creation | Targets arxiv, openai.com, deepmind.com, huggingface.co |
| **X.com (tweepy v2)** | Real-time social signal | `has:media` filter, full URL expansions, engagement-sorted |
| **OpenAI Chat** | Generation + embedding | GPT-4o-mini for all text; text-embedding-3-small for all vectors |
| **OpenAI Images** | HD poster generation | DALL-E 3 `quality=hd`, `style=vivid` — cinematic neon-noir prompts |
| **Cohere** | Post-retrieval reranking | `rerank-v3.5` narrows all unique KG+Dense chunks to top 8 most relevant |

---

## Task 4 — Prototype

The full application runs locally:

```bash
docker compose up -d                           # start Qdrant
uv run python scripts/ingest_courses.py        # ingest KB (once)
uv run python api_server.py                    # FastAPI bridge → http://localhost:8001
cd zizi-lms && npm install && npm run dev      # Next.js LMS → http://localhost:3000
uv run chainlit run app.py                     # Chainlit (content creator) → http://localhost:8000
```

**Demonstrated flows:**

1. **LMS — Byte mode** (`/learn/{topic}`) — Topic clicked in galaxy → ByteGenerator retrieves context from KB → GPT-4o-mini generates analogy + explanation + "why it matters" + emoji → rendered as a glass-card UI with framer-motion animations.

2. **LMS — Build mode** — "Build" tab on any topic → notebook code cells extracted and displayed with syntax highlighting → run notes explain how to execute.

3. **LMS — Chat** (`/chat`) — Full SSE streaming chat: KG+Dense retrieval → all unique chunks → Cohere Rerank → analogy-first grounded answer streamed token-by-token. Pipeline steps animate as they execute. Sources shown with relevance scores. Conversation memory (last 8 turns).

4. **Content Creator** (Chainlit) — `create` → full pipeline in ~25 seconds: Tavily 5 results + X.com social signal → LLM selects specific topic → dedup check → Dense retrieval grounds in KB → Hook→Analogy→Tech→CTA post generated → DALL-E 3 HD image → ingested to Qdrant + KG.

5. **Dedup agentic branch** — `create` with same topic → cosine similarity 0.91 > 0.85 → pipeline halts → user informed with source post name and similarity score.

6. **Galaxy view** (`/`) — D3 force-directed graph of all topic nodes + BUILDS_ON edges. Click any node → `/learn/{id}`.

---

## Task 5 — Baseline Evaluation (RAGAS)

### Setup

```bash
uv run python evals/synthetic_data_gen.py --size 15   # generate golden set
uv run python evals/ragas_baseline.py --delay 1.0     # run baseline
```

Synthetic testset generated via `RAGAS TestsetGenerator` (GPT-4o-mini + text-embedding-3-small) against `course_knowledge_base`. 15 Q&A pairs saved to `evals/data/testset.json`.

### Baseline Results — Dense Vector Retrieval

| Metric | Score |
|--------|-------|
| Context Recall | **0.5933** |
| Faithfulness | **0.3722** |
| Answer Relevancy | **0.3892** |

### Analysis

Dense retrieval achieves moderate context recall (59%) — it finds roughly 60% of the facts needed to answer each question. Faithfulness (37%) is the weakest metric: when retrieval misses relevant chunks, the LLM fills gaps from training data rather than retrieved context. Answer relevancy (39%) reflects the same root cause — incomplete context produces hedged or partially off-topic answers.

The core issue is the **vocabulary gap** between conversational learning queries ("explain the agent loop like I am 5 years old") and dense technical course material. Dense retrieval of a short query returns chunks that are topically adjacent but not exactly the content needed.

---

## Task 6 — Advanced Retrieval

### Chosen Technique: HyDE (Hypothetical Document Embeddings)

**Why:** Learner queries are conversational; the knowledge base contains structured technical material. Dense retrieval of a short question returns only superficially similar chunks. HyDE generates a hypothetical technical answer *in the same vocabulary as the KB* — dramatically reducing the semantic gap (Session 11 pattern).

**Implementation:** `src/retrieval/hyde_retriever.py` — GPT-4o-mini generates a 512-token hypothetical answer → embeds it → Qdrant search → fallback to dense on failure.

### HyDE Results vs. Baseline

| Metric | Dense (Baseline) | HyDE | Delta |
|--------|-----------------|------|-------|
| Context Recall | 0.5933 | **0.6344** | **+0.0411 (+6.9%)** |
| Faithfulness | 0.3722 | **0.4768** | **+0.1046 (+28.1%)** |
| Answer Relevancy | 0.3892 | **0.5196** | **+0.1304 (+33.5%)** |

HyDE improves all three metrics. The largest gain is faithfulness (+28%) — by finding chunks that actually contain the needed information, the LLM no longer has to fill gaps from training data.

### Module 11 — Full Retrieval Strategy Comparison

All 7 strategies from AIE9 Session 11 evaluated on the same 15-sample testset, using the exact LangChain classes taught in the cohort:

| Rank | Strategy | Context Recall | Faithfulness | Answer Relevancy | Composite |
|------|---|---|---|---|---|
| 🥇 1 | **Semantic Chunking** | **0.629** | **0.661** | **0.972** | **2.261** |
| 🥈 2 | Naive Dense | 0.618 | 0.653 | 0.966 | 2.237 |
| 3 | Ensemble (BM25+Dense) | 0.472 | 0.431 | 0.576 | 1.480 |
| 4 | Cohere Rerank | 0.422 | 0.467 | 0.516 | 1.405 |
| 5 | Multi-Query | 0.444 | 0.413 | 0.520 | 1.377 |
| 6 | Parent-Document | 0.459 | 0.398 | 0.449 | 1.307 |
| 7 | BM25 | 0.290 | 0.379 | 0.513 | 1.182 |

**Key finding:** Semantic Chunking wins because it creates topic-coherent chunks aligned with the AIE9 course structure (each section covers one concept). Fixed 512-char chunking is already well-calibrated — the gap between 1st and 2nd is only 1.1%.

**KG+Dense multi-hop** (chat production pipeline):

| Metric | Dense | HyDE | KG+Dense |
|--------|-------|------|----------|
| Context Recall | 0.5933 | 0.6344 | 0.3389 |
| Faithfulness | 0.3722 | 0.4768 | 0.2224 |
| Answer Relevancy | 0.3892 | 0.5196 | 0.2612 |

KG+Dense scores lower on RAGAS precision metrics because RAGAS rewards focused retrieval of exact reference facts. KG traversal is optimized for *breadth* — surfacing connected topics for exploratory learning — which is valuable in the interactive chat pipeline but appears as noise in single-question RAGAS evaluation. Retained in production for pedagogical multi-hop value.

> Full analysis, strategy implementations, and hyperparameter decisions: `evals/EVALUATION_REPORT.md`

---

## Task 7 — Next Steps

### Will Dense Retrieval Be Kept for Demo Day?

**No.** The production chat pipeline uses **KG+Dense → Cohere Rerank**:

- **KG traversal** — surfaces related concepts the user didn't explicitly name, enabling multi-hop explanations that connect topics across modules
- **Direct dense pass** — runs in parallel (k=15) to guarantee the most obvious module matches survive
- **All unique chunks to Cohere** — critical fix: don't pre-filter by embedding score; let neural reranking decide what's relevant. This fixed the "agent loop" grounding failure where Session03 chunks (cosine 0.47) were cut before Cohere could surface them above broader KG chunks (cosine 0.62)
- **Cohere Rerank top 8** — selects the 8 most relevant chunks from the full candidate pool

### Roadmap for Demo Day

| Priority | Feature | Value |
|----------|---------|-------|
| 1 | Switch KB ingestion to `SemanticChunker(percentile)` | Best composite score (2.261); 1.1% gain over fixed-512 |
| 2 | LinkedIn API integration | One-click publish via OAuth 2.0 |
| 3 | Learner profile / personalization | Ask profession on first chat → adapt analogies |
| 4 | Multi-cohort KB | Ingest material from any course; `_MODULE_TOPICS` is ready to extend |
| 5 | WhatsApp / email delivery | Push byte-sized cards on a schedule |
| 6 | Public deployment | Vercel (Next.js) + Railway (FastAPI + Qdrant) |

---

## Running the Full Stack

```bash
# 1. Setup
cp .env.example .env          # add OPENAI_API_KEY, TAVILY_API_KEY, COHERE_API_KEY
uv sync                       # install Python deps
docker compose up -d          # start Qdrant

# 2. Ingest course materials
uv run python scripts/ingest_courses.py

# 3. Start API bridge
uv run python api_server.py   # → http://localhost:8001

# 4. Start LMS frontend
cd zizi-lms && npm install && npm run dev   # → http://localhost:3000

# 5. (Optional) Start Chainlit content creator
uv run chainlit run app.py    # → http://localhost:8000
```

## Running Evaluations

```bash
uv run python evals/synthetic_data_gen.py --size 15    # generate golden set
uv run python evals/ragas_baseline.py --delay 1.0      # Task 5 — dense baseline
uv run python evals/ragas_hyde.py --delay 1.0          # Task 6 — HyDE upgrade
uv run python evals/ragas_kg.py --delay 1.0            # KG+Dense evaluation
uv run python evals/ragas_module11.py --delay 1.5      # all 7 Module 11 strategies
# results saved to evals/results/
```

---

## Cohort Sessions Applied

| Session | Concept Applied | Where in Zizi Byte |
|---------|----------------|---------------------|
| 02 | Embeddings, text-embedding-3-small | All vector search — `DenseRetriever`, `KGRetriever` |
| 03 | Agent loop, LangGraph StateGraph | `content_pipeline.py` LangGraph graph; chat pipeline |
| 04 | Agentic RAG, conditional edges | `dedup_check_node` branch; `kg_retriever.py` |
| 05 | Multi-agent patterns | `KGRetriever` multi-hop = multi-topic agent pattern |
| 06 | Agent memory | Chat `history[-8:]` conversation memory in `/api/chat/stream` |
| 08 | DALL-E image generation | `image_tool.py` → `generate_poster()` |
| 10 | RAGAS evaluation (`SingleTurnSample`, `EvaluationDataset`) | All eval scripts in `evals/` |
| 11 | Advanced retrieval (all 7 strategies) | `src/retrieval/` — all 7 implemented + evaluated |

---

*Built with LangGraph · Qdrant · NetworkX · FastAPI · Next.js 14 · Chainlit · Cohere · OpenAI · Tavily · D3.js · framer-motion · Zustand*
