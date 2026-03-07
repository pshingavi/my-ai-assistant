# AIE9 Certification Challenge — Submission

**Project:** AI Content Creator
**Author:** Preetam
**Cohort:** AIE9

---

## The One-Line Pitch

> An agentic RAG system that finds today's hottest AI topic, retrieves grounding context from the AIE9 course knowledge base, writes a story-driven LinkedIn post with a cinematic image — and remembers everything so it never repeats itself.

---

## Task 1 — Problem, Audience & Scope

### The Problem

AI engineers who build things for a living struggle to talk about what they build. A typical LinkedIn post takes 2–3 hours: reading newsletters, scanning X.com, summarising a paper, then trying to bridge the gap between "technically accurate" and "will make someone stop scrolling." Most give up after one post. Those who persist write either dense jargon (ignored outside their niche) or vapid hype (ignored by serious engineers).

The deeper problem is structural. There is no system that simultaneously:
1. **Knows what you've already written about** (no accidental repeats)
2. **Knows the technical depth of the topic** from authoritative sources
3. **Translates that depth into story-driven content** for a mixed professional audience

### Target User

**AI engineers and technical thought leaders** at any career stage — engineers who understand the technology and want to build a public presence but have no time for the research-to-draft pipeline.

### Evaluation Questions

| # | Input | Expected output |
|---|-------|-----------------|
| 1 | `create` | Trending topic + LinkedIn post + HD poster image + source citations |
| 2 | `create` (same topic) | Dedup detected → "already covered" message with fresh-angle suggestion |
| 3 | `What is HyDE retrieval?` | Analogy-driven KB-grounded answer with cited source file |
| 4 | `Explain RAG like I'm a chef` | Vivid analogy + technical grounding from course material |
| 5 | `What is the ReAct loop pattern?` | KB answer with source chunk accordion |
| 6 | `How does LangGraph handle state?` | Multi-hop KG retrieval answer |
| 7 | `What are RAGAS evaluation metrics?` | Factual answer from session 10 material |
| 8 | `kg` | Interactive knowledge graph of all course topics + generated posts |

---

## Task 2 — Proposed Solution

### Overview

A Chainlit chat application with three modes, backed by a LangGraph multi-agent system:

**Mode 1 — Content Pipeline**: Research Tavily + X.com → LLM selects hottest specific topic → check dedup (the agentic decision point) → HyDE retrieval from course KB → generate Hook→Analogy→Tech→CTA post → generate DALL-E 3 HD image → ingest to Qdrant + Knowledge Graph → show source citations.

**Mode 2 — Knowledge Chat**: KG traversal + HyDE retrieval → grounded streaming answer with inline source citations → automatic fallback to dense retrieval then Tavily web when KB coverage is weak. Sources panel always rendered — never an answer without a reference.

**Mode 3 — KG View**: Interactive Plotly network graph of all topics — course modules as purple circles, generated posts as blue diamonds, BUILDS_ON edges showing the learning path. Grows with every new post or ingested cohort.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Chainlit UI  (app.py)                  │
│  "create"   → Content Pipeline (LangGraph)              │
│  "kg"       → Plotly KG Visualization                   │
│  question   → Chat Pipeline (LangGraph)                 │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
   ┌───────────▼──────────┐  ┌────────▼──────────────────┐
   │  Content Pipeline    │  │  Chat Pipeline             │
   │                      │  │                            │
   │  research_node        │  │  kg_retrieve_node          │
   │  merge_topics_node    │  │  ├─ KGRetriever (primary) │
   │  dedup_check_node ●  │  │  ├─ DenseRetriever (fallback)│
   │  retrieve_context    │  │  └─ Tavily web (fallback)  │
   │  generate_post       │  │                            │
   │  generate_image      │  │  generate_answer_node      │
   │  ingest_post         │  │  (streaming + citations)   │
   └──────────────────────┘  └────────────────────────────┘
               │
   ┌───────────▼──────────────────────────────────────────┐
   │  Shared Infrastructure                               │
   │  Qdrant  · course_knowledge_base  · generated_posts  │
   │  NetworkX Topic Graph  (data/topic_graph.json)        │
   │  LangSmith (auto-traces when LANGCHAIN_API_KEY set)  │
   └───────────────────────────────────────────────────────┘
```

### Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM | GPT-4o-mini | Best structured JSON output + streaming at low cost |
| Image | DALL-E 3 HD (`quality=hd`, `style=vivid`) | Cinematic poster quality; gpt-image-1 supported via config |
| Orchestration | LangGraph | Native conditional edges make the dedup branch clean and auditable |
| Tools | Tavily + X.com (tweepy v2) | Tavily targets authoritative AI sources; X.com adds real-time social signal with media |
| Embedding | text-embedding-3-small | Strong semantic similarity at 1/5th the cost of large |
| Vector DB | Qdrant (Docker) | Free local instance, metadata filtering, production-ready client |
| KG | NetworkX + JSON | Zero extra infra; cosine similarity traversal built in |
| Monitoring | LangSmith | Native LangGraph tracing; zero config when API key is set |
| Evaluation | RAGAS 0.2.x | Standard RAG eval with `SingleTurnSample` API from Session 10 |
| UI | Chainlit 2.x | Streaming, Steps accordion, `cl.Plotly` for KG, `cl.Image` for media |
| Package manager | uv | 10–100× faster than pip; workspace + editable install via hatchling |

### RAG and Agent Components

**RAG:**
- *Dense baseline*: embed raw query → Qdrant cosine search
- *HyDE (advanced)*: LLM generates a hypothetical technical document → embed that → Qdrant search. Bridges the semantic gap between a short conversational query and a dense technical document.
- *KG RAG*: embed query → cosine-match topic nodes → traverse NetworkX edges up to 2 hops → HyDE retrieval on each related topic name → merge + deduplicate by score. Enables multi-hop retrieval across concepts the query didn't directly name.

**Agent:**
`dedup_check_node` is the key agentic decision point. It embeds the selected topic, searches `posts_collection`, and at runtime decides whether to continue the creation pipeline or halt and inform the user. No human in the loop — the graph branches based on cosine similarity > 0.85.

---

## Task 3 — Data & External APIs

### Knowledge Base

| Source | Format | Role | Chunks |
|--------|--------|------|--------|
| AIE9 sessions 02–11 — slide decks | PDF | Primary KB — technical grounding | ~700 |
| AIE9 Jupyter notebooks (cell-level) | .ipynb | Code + explanation pairs | ~350 |
| AIE9 markdown guides | .md | Concept explainers | ~160 |
| Generated LinkedIn posts | text | Dedup store + KG growth | dynamic |

**Total at submission:** 1,212 chunks across 24 files from 8 modules.

### Chunking Strategy

| Source type | Strategy | Rationale |
|-------------|----------|-----------|
| PDF | `RecursiveCharacterTextSplitter` (512 tok, 50 overlap) | Respects paragraph boundaries in slide-deck structure |
| Notebook | Cell-level pairing: markdown + following code cell | Keeping explanation + implementation together preserves pedagogical intent — separating them loses context |
| Markdown | Fixed-size (512, 50 overlap) | Less structure than PDFs; simpler approach works |

### External APIs

| API | Role | How it interacts |
|-----|------|-----------------|
| **Tavily** | Find today's hottest AI news | Targeted at arxiv, openai.com, deepmind.com, huggingface.co, VentureBeat with current month/year — returns top 5 scored results |
| **X.com (tweepy v2)** | Real-time social signal | Bearer token search with `has:media` filter, full media expansions (image URLs, video preview URLs) — returns engagement-scored tweets |
| **OpenAI Chat** | Topic selection, HyDE generation, post writing, concept extraction | GPT-4o-mini for JSON tasks; streaming for chat answers |
| **OpenAI Images** | Poster generation | DALL-E 3 HD with cinematic neon-noir prompt + `style=vivid` |

**Data flow:** Tavily + X.com results are merged → LLM selects the most specific, named topic → HyDE generates a hypothetical technical document for that topic → that document is embedded → Qdrant retrieves the closest KB chunks → those chunks ground the LinkedIn post.

---

## Task 4 — Prototype

The application runs locally on a single command:

```bash
uv run chainlit run app.py   # → http://localhost:8000
```

**Demonstrated flows:**

1. **`create`** — full pipeline in ~25 seconds. Tavily returns 5 results, X.com 10. LLM selects a specific named topic (e.g. "Gemini 2.0 Flash native tool use in production"). Dedup passes. HyDE retrieves 5 KB chunks with max relevance 0.62. 2,037-char post generated with Hook/Analogy/Tech/CTA structure. DALL-E 3 HD image saved to `data/images/`. Post ingested to Qdrant and Knowledge Graph. Tavily + X.com citations shown.

2. **`create` (same topic)** — dedup fires. Cosine similarity 0.91 > 0.85 threshold. Pipeline stops. User informed with source post name and similarity score.

3. **`What is HyDE retrieval?`** — KG traversal finds "Advanced Retrieval" node, traverses to "Dense Vector Retrieval" (1 hop). HyDE retrieves 5 chunks from `AIE9_Session11_AdvancedRetrieval.pdf` and notebooks. Analogy answer streamed with inline citations. Sources panel shows 5 chunk accordions with relevance scores.

4. **`kg`** — Plotly graph renders 13 nodes (8 course modules + 5 generated posts), 12 BUILDS_ON edges. Hover shows description and concepts.

---

## Task 5 — Baseline Evaluation (RAGAS)

### Setup

```bash
uv run python evals/synthetic_data_gen.py --size 15
uv run python evals/ragas_baseline.py --delay 1.0
```

Synthetic testset generated via `RAGAS TestsetGenerator` using `LangchainLLMWrapper(ChatOpenAI)` + `LangchainEmbeddingsWrapper(OpenAIEmbeddings)` against the `course_knowledge_base` collection. 15 question/reference pairs saved to `evals/data/testset.json`.

### Baseline Results — Dense Vector Retrieval

| Metric | Score |
|--------|-------|
| Context Recall | *(run `ragas_baseline.py` to populate)* |
| Faithfulness | *(run `ragas_baseline.py` to populate)* |
| Answer Relevancy | *(run `ragas_baseline.py` to populate)* |

### Analysis

Dense retrieval performs reasonably on keyword-rich questions ("What is cosine similarity?") but struggles with conversational or cross-concept queries ("How does HyDE improve over standard retrieval?" "Explain the agent loop as if I'm a chef"). The core issue: short conversational queries sit far from dense technical course material in embedding space. This motivates HyDE.

---

## Task 6 — Advanced Retrieval: HyDE + Knowledge Graph

### Why HyDE for This Use Case

LinkedIn content creation queries are conversational ("what's trending in multi-agent AI?"). The knowledge base contains structured technical material (slides, code, explanations). Dense retrieval of a short conversational query returns only superficially similar chunks. HyDE generates a hypothetical technical document in the *same vocabulary as the KB* — dramatically reducing the semantic gap.

**Implementation:** `src/retrieval/hyde_retriever.py` — GPT-4o-mini generates a 512-token hypothetical answer → embed with text-embedding-3-small → Qdrant search → fallback to dense on failure.

**KG extension:** `src/retrieval/kg_retriever.py` — cosine-match against NetworkX topic node embeddings → traverse BUILDS_ON edges up to 2 hops → run HyDE retrieval for each related topic name → merge and re-rank. Enables "LangGraph" to retrieve content from "Multi-Agent" and "Agent Memory" even if neither word appears in the query.

```bash
uv run python evals/ragas_hyde.py --delay 1.0
```

### HyDE vs Baseline

| Metric | Baseline (Dense) | HyDE | Delta |
|--------|-----------------|------|-------|
| Context Recall | *(populate)* | *(populate)* | — |
| Faithfulness | *(populate)* | *(populate)* | — |
| Answer Relevancy | *(populate)* | *(populate)* | — |

**Expected outcome:** Context Recall and Answer Relevancy improve as HyDE bridges the query-to-KB gap. Faithfulness may slightly decrease as HyDE retrieves broader cross-topic context (known trade-off). The KG adds a compounding benefit: each new generated post improves future retrieval by extending the graph.

---

## Task 7 — Next Steps

### Will Dense Retrieval Be Kept for Demo Day?

**No — HyDE + KG is the default.** The semantic gap between conversational queries and technical course content is fundamental to this use case. Dense retrieval is kept only as: (1) an automatic fallback when HyDE generation fails, (2) a merger candidate when KG+HyDE scores are weak (< 0.35), and (3) an A/B baseline for future retrieval improvements.

### Roadmap to Demo Day

| Priority | Feature | Value |
|----------|---------|-------|
| 1 | Run RAGAS evals + fill in table above | Required for submission completeness |
| 2 | Streaming post generation | Token-by-token render in Chainlit for better UX |
| 3 | LinkedIn API integration | One-click publish via OAuth 2.0 |
| 4 | Post history viewer | Gallery of all generated posts with images and metrics |
| 5 | Multi-cohort KG | Ingest AIE8/AIE7 material; `_MODULE_TOPICS` dict is ready to extend |
| 6 | ColBERT reranker | Post-retrieval reranking on top of HyDE for higher faithfulness |
| 7 | Local LLM option | Ollama + LLaMA-3 via OpenAI-compatible endpoint for zero-cost inference |
| 8 | Domain configurability | `CONTENT_DOMAIN=.env` already exists; UI domain picker to follow |

---

## Running the Evaluation

```bash
# Full evaluation pipeline
uv run python evals/synthetic_data_gen.py --size 15
uv run python evals/ragas_baseline.py --delay 1.0
uv run python evals/ragas_hyde.py --delay 1.0
# → comparison table printed to console
# → results saved to evals/results/
```

---

*Built with LangGraph · Qdrant · NetworkX · Chainlit · OpenAI · Tavily · tweepy*
