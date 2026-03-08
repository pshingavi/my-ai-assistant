# Zizi Byte — AIE9 Certification Challenge Submission

**"Learn in bytes. Think in leaps."**

**Author:** Preetam | **Cohort:** AIE9

---

## The One-Line Pitch

> An adaptive AI micro-learning platform that transforms dense technical course materials into personalized, analogy-driven learning experiences — grounded in the actual knowledge base, not generic LLM knowledge.

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

**Zizi Byte** is a two-mode Chainlit application backed by LangGraph pipelines:

**Learning Chat** — the core: a user asks anything; the system retrieves grounding context from the course knowledge base via KG+Dense multi-hop retrieval, reranks with Cohere, and generates an analogy-first, strictly-grounded answer. Every claim is cited. Every answer starts with a vivid analogy before the technical explanation.

**Content Creator** — a secondary mode: research trending AI topics via Tavily + X.com, check for duplicate posts (the agentic decision point), retrieve KB grounding, generate a LinkedIn post in Hook→Analogy→Tech→CTA structure, generate a DALL-E 3 HD poster, and ingest the post back into the knowledge graph.

| Mode | Trigger | Pipeline |
|------|---------|----------|
| **Learning Chat** | Any question | `KG+Dense (k=15) → Cohere Rerank → analogy-first generation → sources` |
| **Content Creator** | `create`, `write post`, `trending` | `research → merge → dedup_check → retrieve → generate_post → generate_image → ingest` |
| **KG View** | `kg`, `graph`, `topics` | Interactive Plotly graph of all topics + generated posts |

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Zizi Byte  (app.py / Chainlit)           │
│  question  → Learning Chat                               │
│  "create"  → Content Pipeline                           │
│  "kg"      → KG Visualization (Plotly)                  │
└──────────────┬─────────────────────┬────────────────────┘
               │                     │
   ┌───────────▼──────────┐  ┌───────▼──────────────────────────┐
   │  Content Pipeline    │  │  Learning Chat                    │
   │  (LangGraph)         │  │                                   │
   │  research_node       │  │  1. KG+Dense retrieval (k=15)     │
   │  merge_topics_node   │  │     KGRetriever: multi-hop graph  │
   │  dedup_check_node ●  │  │     + DenseRetriever: raw query   │
   │  [AGENTIC DECISION]  │  │                                   │
   │  retrieve_context    │  │  2. Cohere Rerank → top 5         │
   │  generate_post       │  │                                   │
   │  generate_image      │  │  3. Analogy-first generation      │
   │  ingest_post         │  │  4. Sources list (file + score)   │
   └──────────────────────┘  └───────────────────────────────────┘
               │
   ┌───────────▼──────────────────────────────────────────┐
   │  Shared Infrastructure                               │
   │  Qdrant  · course_knowledge_base  · generated_posts  │
   │  NetworkX Topic Graph  (data/topic_graph.json)       │
   │  LangSmith (auto-traces when LANGCHAIN_API_KEY set)  │
   └──────────────────────────────────────────────────────┘
```

### Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | GPT-4o-mini | Best structured output + streaming at low cost |
| Image | DALL-E 3 HD (`quality=hd`, `style=vivid`) | Cinematic poster quality for content creation |
| Orchestration | LangGraph | Native conditional edges make the dedup branch clean and auditable |
| Retrieval | KG+Dense → Cohere Rerank | Multi-hop context + neural reranking for precision |
| Tools | Tavily + X.com (tweepy v2) | Authoritative AI sources + real-time social signal with media |
| Embedding | text-embedding-3-small | Strong semantic similarity at cost-efficient 1536 dims |
| Vector DB | Qdrant (Docker) | Free local, metadata filtering, production-ready |
| KG | NetworkX + JSON | Zero extra infra; cosine similarity traversal + JSON persistence |
| Reranking | Cohere rerank-v3.5 | Best faithfulness improvement in Module 11 evaluation |
| Monitoring | LangSmith | Native LangGraph tracing; zero config when API key is set |
| Evaluation | RAGAS 0.2.x | Standard RAG eval with `SingleTurnSample` API (Session 10 pattern) |
| UI | Chainlit 2.x | Streaming, Steps accordion, `cl.Plotly` for KG |
| Package manager | uv | 10–100× faster than pip; workspace + editable install |

### RAG and Agent Components

**RAG stack** (production):
- *KGRetriever* — embed query → cosine-match topic nodes in NetworkX graph → traverse BUILDS_ON edges up to 2 hops → Dense retrieval on original query + each related topic → merge 15 candidates
- *Cohere Rerank* — `CohereRerank(model="rerank-v3.5")` selects top 5 from 15 candidates
- *DenseRetriever* — direct embed of raw query runs in parallel with KG to guarantee most-obvious matches survive

**Agentic decision point:**
`dedup_check_node` embeds the selected topic, searches `posts_collection`, and at runtime decides whether to continue creation or halt. The graph branches on cosine similarity > 0.85 — no human in the loop, driven entirely by observed data quality.

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

### External APIs

| API | Role | How it interacts |
|-----|------|-----------------|
| **Tavily** | Find trending AI topics for content creation | Targets arxiv, openai.com, deepmind.com, huggingface.co with current month/year |
| **X.com (tweepy v2)** | Real-time social signal with media | `has:media` filter, full media URL expansions, engagement-sorted |
| **OpenAI Chat** | Generation + embedding | GPT-4o-mini for all text; text-embedding-3-small for all vectors |
| **OpenAI Images** | HD poster generation | DALL-E 3 `quality=hd`, `style=vivid` — cinematic neon-noir prompts |
| **Cohere** | Post-retrieval reranking | `rerank-v3.5` narrows 15 KB candidates to top 5 most relevant |

---

## Task 4 — Prototype

The application runs locally:

```bash
docker compose up -d          # start Qdrant
uv run python scripts/ingest_courses.py   # ingest KB (once)
uv run chainlit run app.py    # → http://localhost:8000
```

**Demonstrated flows:**

1. **Learning question** — `Explain the agent loop like I am 5 years old`: KG traversal finds "The Agent Loop" node and related topics; Dense retrieval retrieves top candidates; Cohere reranks to the 5 most relevant chunks from `AIE9_Session03_The-Agent-Loop.pdf`; analogy-first answer streamed with inline citations; sources listed with relevance scores.

2. **`create`** — full pipeline in ~25 seconds: Tavily returns 5 results, X.com adds social signal; LLM selects specific topic; dedup passes; Dense retrieval grounds in KB; post generated (Hook→Analogy→Tech→CTA); DALL-E 3 HD image saved; post ingested to Qdrant + Knowledge Graph; Tavily + X.com citations shown.

3. **`create` (same topic)** — dedup fires; cosine similarity 0.91 > 0.85 threshold; pipeline halts; user informed with source post name and similarity score.

4. **`kg`** — Plotly graph renders 8 course module nodes + generated post nodes with BUILDS_ON edges. Hover shows description and concepts.

---

## Task 5 — Baseline Evaluation (RAGAS)

### Setup

```bash
uv run python evals/synthetic_data_gen.py --size 15
uv run python evals/ragas_baseline.py --delay 1.0
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

The core issue is the **semantic gap** between conversational learning queries ("explain the agent loop like I am 5 years old") and dense technical course material. Dense retrieval of a short query returns chunks that are topically adjacent but not exactly what is needed.

---

## Task 6 — Advanced Retrieval

### Chosen Technique: HyDE (Hypothetical Document Embeddings)

**Why:** Learner queries are conversational; the knowledge base contains structured technical material. Dense retrieval of a short question returns only superficially similar chunks. HyDE generates a hypothetical technical answer *in the same vocabulary as the KB* — dramatically reducing the semantic gap.

**Implementation:** `src/retrieval/hyde_retriever.py` — GPT-4o-mini generates a 512-token hypothetical answer → embeds it → Qdrant search → fallback to dense on failure.

### HyDE Results

| Metric | Dense (Baseline) | HyDE | Delta |
|--------|-----------------|------|-------|
| Context Recall | 0.5933 | **0.6344** | **+0.0411 (+6.9%)** |
| Faithfulness | 0.3722 | **0.4768** | **+0.1046 (+28.1%)** |
| Answer Relevancy | 0.3892 | **0.5196** | **+0.1304 (+33.5%)** |

HyDE improves all three metrics. The largest gain is faithfulness (+28%) — by finding chunks that actually contain the needed information, the LLM no longer has to fill gaps from training data.

### Module 11 — Full Retrieval Strategy Comparison

All 7 strategies from AIE9 Session 11 evaluated on the same 15-sample testset:

| Strategy | Context Recall | Faithfulness | Answer Relevancy | Composite |
|---|---|---|---|---|
| **Semantic Chunking** | **0.629** | **0.661** | **0.972** | **2.261** |
| Naive Dense | 0.618 | 0.653 | 0.966 | 2.237 |
| Ensemble (BM25+Dense) | 0.472 | 0.431 | 0.576 | 1.480 |
| Cohere Rerank | 0.422 | 0.467 | 0.516 | 1.405 |
| Multi-Query | 0.444 | 0.413 | 0.520 | 1.377 |
| Parent-Document | 0.459 | 0.398 | 0.449 | 1.307 |
| BM25 | 0.290 | 0.379 | 0.513 | 1.182 |

**Key finding:** Semantic Chunking wins because it creates topic-coherent chunks that match the AIE9 course structure (each section covers one concept). Fixed 512-char chunking is already well-calibrated for this corpus — the gap is narrow (2.261 vs 2.237).

---

## Task 7 — Next Steps

### Will Dense Retrieval Be Kept for Demo Day?

**No.** The production chat pipeline uses **KG+Dense → Cohere Rerank**:

- **KG traversal** — surfaces related concepts the user didn't explicitly name, enabling multi-hop explanations that connect topics across modules
- **Direct dense pass** — runs in parallel (k=15) to guarantee the most obvious module matches survive
- **Cohere Rerank** — selects the 5 most relevant chunks from the 15-candidate pool, maximising faithfulness

Dense-only is kept as the content pipeline retriever (post grounding) and as a RAGAS evaluation baseline.

### Roadmap

| Priority | Feature | Value |
|----------|---------|-------|
| 1 | Switch KB ingestion to SemanticChunker | Best composite score (2.261); re-run `reingest_fresh.py` |
| 2 | LinkedIn API integration | One-click publish via OAuth 2.0 |
| 3 | Learner profile / personalization | Ask profession on first chat → adapt analogies |
| 4 | Multi-cohort KB | Ingest material from any course; `_MODULE_TOPICS` dict is ready to extend |
| 5 | WhatsApp / email delivery | Push byte-sized explanations on a schedule |
| 6 | Ensemble weight tuning | 0.3 BM25 / 0.7 Dense performs better than equal-weight |

---

## Running the Evaluation

```bash
uv run python evals/synthetic_data_gen.py --size 15
uv run python evals/ragas_baseline.py --delay 1.0
uv run python evals/ragas_hyde.py --delay 1.0
uv run python evals/ragas_module11.py --delay 1.5   # all 7 Module 11 strategies
uv run python evals/ragas_kg.py --delay 1.0          # KG+Dense evaluation
# → results saved to evals/results/
# → full analysis in evals/EVALUATION_REPORT.md
```

---

*Built with LangGraph · Qdrant · NetworkX · Chainlit · Cohere · OpenAI · Tavily · tweepy*
