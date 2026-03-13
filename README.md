# Zizi Byte

**"Learn in bytes. Think in leaps."**

> An adaptive AI micro-learning platform that transforms dense technical course materials
> into personalized, analogy-driven, interactive learning experiences — powered by RAG,
> Knowledge Graph traversal, Cohere reranking, and Claude Sonnet-generated SVG animations.
>
> Named after Ziva — because learning should feel like play, not like work.

Built as the **AIE9 Certification Challenge** final submission by Preetam (AIE9 cohort).

---

## The Problem

Dense technical courses — PDFs, Jupyter notebooks, code — are hard to retain and connect across modules. Learners struggle to:

1. **Retain** concepts from week-to-week (each session is 50-200 slides + notebooks)
2. **Connect** ideas across modules (e.g., Module 02 embeddings → Module 11 reranking → Module 09 LangSmith)
3. **Apply** abstract AI/ML concepts to their own professional context

**Zizi Byte's answer:** RAG retrieval over the actual course knowledge base, two-step mechanism research, analogy-first explanations, interactive p5.js visualizations, grounded technical deep dives — and a chat interface that cites every claim to its source file.

---

## What It Does — Three Surfaces

### 1. LMS — Byte-Sized Learning (`localhost:3000`)

Every concept gets a complete **Zizi Byte**: one focused learning artifact that covers the concept from three angles:

**Learn Mode — 3 tabs:**

| Tab | What It Shows |
|-----|---------------|
| **Analogy** | Simple everyday analogy (Claude Sonnet 4.6, evaluated for simplicity/clarity/memorability) + DALL-E 3 image + why it matters |
| **Interactive** | Claude Sonnet 4.6-generated SVG animation in a sandboxed iframe. 5 discrete steps with Next/Prev navigation and anime.js transitions. Fires `postMessage` to sync the React step panel. |
| **Deep Dive** | Verbatim technical explanation grounded in RAG-retrieved course chunks, with source citations |

**Build Mode:**
- Same interactive widget as Learn (shared API endpoint, no re-fetch)
- Code panel syncs to current step via `postMessage` — shows code snippet + explanation per step
- "Download Notebook" button: returns best matching `.ipynb` from indexed course materials

**Share Mode:**
- LinkedIn post generation (uses exact byte analogy, ZiziByte attribution appended)
- Custom angle input for tailoring the post
- Image download, Notebook download

**Regenerate with custom analogy:**
- Clicking Regenerate opens a slide-down panel with 3 LLM-generated alternative analogies + a custom text input
- Selecting or submitting clears all caches and regenerates the byte, sketch, and deep dive from scratch

### 2. Chat — Grounded Q&A (`localhost:8000` via Chainlit)

Ask anything about the AIE9 course content:

```
KG traversal + DenseRetriever (k=15 each)
         ↓
   Cohere Rerank (top 8)
         ↓
  GPT-4o streaming answer
  analogy-first, RAG-grounded
  cites every source file
```

- Every answer leads with an analogy, then technical explanation grounded exclusively in retrieved course chunks
- Sources shown with relevance scores
- 8-turn conversation memory
- Streaming SSE

### 3. Content Pipeline — AI Content Creator (via Chainlit or Share mode)

```
Tavily research + X search
         ↓
     Topic selection
         ↓
  Dedup check (cosine similarity vs ingested posts)
         ↓
  RAG context retrieval
         ↓
  GPT-4o LinkedIn post
         ↓
  DALL-E 3 image
         ↓
  Ingest to Qdrant (prevents future duplicates)
```

The `dedup_check_node` is the agentic decision point — branches to `inform_duplicate` if cosine similarity > threshold.

---

## Architecture

> **D2 diagram**: See [`docs/zizi-byte-architecture.d2`](docs/zizi-byte-architecture.d2) for a detailed diagram. Build with `d2 docs/zizi-byte-architecture.d2 docs/zizi-byte-architecture.svg` — [D2 install](https://d2lang.com/tour/intro/).

```mermaid
flowchart TB
    subgraph Entry["User Entry Points"]
        CL[Chainlit :8000]
        LMS[Next.js LMS :3000]
    end

    API[FastAPI :8001]

    subgraph Content["Content Pipeline (LangGraph)"]
        R[research]
        M[merge_topics]
        D[dedup_check]
        RC[retrieve_context]
        GP[generate_post]
        GI[generate_image]
        IN[ingest_post]
    end

    subgraph Chat["Chat Pipeline"]
        KG[KGRetriever]
        DR[DenseRetriever]
        CR[Cohere Rerank]
        GEN[generate_answer]
    end

    subgraph Byte["Byte Pipeline (LMS)"]
        CACHE[check_cache]
        AG[analogy_generator]
        FAN[image | animation | TTS]
        PERSIST[persist]
    end

    subgraph AI["AI Services"]
        OAI[OpenAI]
        CO[Cohere]
    end

    subgraph Mem["Memory"]
        QD[(Qdrant)]
        TG[(Topic Graph)]
        SQL[(SQLite)]
    end

    subgraph Tools["Tools"]
        TV[Tavily]
        X[X.com]
    end

    CL --> API
    LMS --> API
    API --> Content
    API --> Chat
    API --> Byte
    Content --> AI
    Chat --> AI
    Byte --> AI
    Content --> Mem
    Chat --> Mem
    Byte --> SQL
    Content --> Tools
    R --> M --> D --> RC --> GP --> GI --> IN
    KG --> CR
    DR --> CR
    CR --> GEN
    CACHE --> AG --> FAN --> PERSIST
```

### ASCII View

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 14 LMS Frontend  (localhost:3000)                      │
│  ByteCardV2 · InteractivePlayer · RegeneratePanel · BuildCard      │
│  ShareModal · TopicDrawer · ConceptDots                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP / JSON
┌─────────────────────▼───────────────────────────────────────────┐
│  FastAPI LMS API  (localhost:8001)  — api_server.py             │
│  /api/topics · /api/bytes · /api/topic/*/p5sketch               │
│  /api/topic/*/analogy-suggestions · /api/topic/*/notebook       │
└──────┬───────────────┬──────────────────────────────────────────┘
       │               │
┌──────▼──────┐ ┌──────▼──────────────────────────────────────────┐
│  SQLite DB  │ │  src/lms/                                        │
│ analogies   │ │  ByteGenerator · P5SketchGenerator               │
│ p5_sketches │ │  analogy_pipeline (LangGraph)                    │
│ warm_jobs   │ │  analogy_store · learning_path                   │
└─────────────┘ └──────┬──────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────┐
│  Retrieval Stack                                                  │
│  DenseRetriever · HyDERetriever · KGRetriever                    │
│                                                                   │
│  Vector Store: Qdrant (Docker, localhost:6333)                    │
│  Knowledge Graph: NetworkX DiGraph → data/topic_graph.json       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Chainlit App  (localhost:8000)  — app.py                        │
│  Intent routing → LMS link / Chat pipeline / Content pipeline    │
└──────────────────────────────────────────────────────────────────┘
```

### Key Files

| File / Dir | Purpose |
|---|---|
| `api_server.py` | FastAPI bridge — all LMS JSON endpoints |
| `app.py` | Chainlit chat app — intent router |
| `src/lms/analogy_pipeline.py` | LangGraph byte pipeline: RAG → research → analogy → image → persist |
| `src/lms/claude_interaction_generator.py` | Claude Sonnet 4.6 SVG animation generator — template shell + JSON fill |
| `src/lms/byte_generator.py` | ByteGenerator — analogy, build content, analogy suggestions |
| `src/lms/analogy_store.py` | SQLite store — analogies, claude_interactions tables |
| `src/agents/content_pipeline.py` | LangGraph content pipeline — research → dedup → RAG → post → image → ingest |
| `src/agents/chat_pipeline.py` | Chat pipeline — KG+Dense → Cohere → GPT-4o stream |
| `src/retrieval/` | DenseRetriever, HyDERetriever, KGRetriever |
| `src/memory/qdrant_store.py` | Qdrant upsert/search |
| `src/memory/topic_graph.py` | NetworkX KG singleton |
| `zizi-lms/src/components/ByteCardV2.tsx` | Main learn card — hero (topic/concept/analogy) + 3 tabs |
| `zizi-lms/src/components/InteractivePlayer.tsx` | Sandboxed Claude SVG iframe with theme CSS injection |
| `zizi-lms/src/components/RegeneratePanel.tsx` | Slide-down panel — 3 suggestions + custom analogy input (pre-populated) |
| `zizi-lms/src/components/BuildCard.tsx` | Build mode — widget + animated code panel |
| `zizi-lms/src/components/ShareModal.tsx` | Share mode — LinkedIn post + image + notebook download |
| `evals/` | RAGAS evaluation pipeline (baseline + HyDE) |
| `scripts/` | ingest_courses.py, warm_cache.py, regen_analogies.py, regen_images.py, regen_interactions.py |

---

## Tech Stack

**Backend**
- Python 3.11+, FastAPI, LangGraph, LangChain
- OpenAI GPT-4o (generation, step metadata), DALL-E 3 (analogy images)
- Anthropic Claude Sonnet 4.6 (analogy generation, evaluation, SVG interaction generation)
- Qdrant (vector store), NetworkX (knowledge graph)
- Cohere Rerank v3.5, HyDE retrieval
- SQLite + aiosqlite (analogies + claude_interactions cache)
- Tavily (web research), tweepy (X/Twitter)
- RAGAS 0.2.x (evaluation)

**Frontend**
- Next.js 14 (App Router), TypeScript, Tailwind CSS
- Framer Motion (all animations)
- anime.js 3.2 (SVG step transitions inside interactive widget iframe)
- Zustand (LMS state), react-hot-toast

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for Qdrant)
- `uv` package manager

### 1. Environment

```bash
cp .env.example .env
# Edit .env — set:
# OPENAI_API_KEY=sk-...     (required)
# TAVILY_API_KEY=tvly-...   (required)
# COHERE_API_KEY=...        (optional, enables reranking)
# LANGCHAIN_API_KEY=...     (optional, enables LangSmith tracing)
# X_BEARER_TOKEN=...        (optional, enables X/Twitter search)
```

### 2. Install & Ingest

```bash
# Python dependencies
uv sync

# Start Qdrant vector store
docker compose up -d

# Ingest course materials (PDFs, notebooks, markdown)
uv run python scripts/ingest_courses.py
```

### 3. Start All Services

```bash
# Terminal 1: FastAPI LMS API
uv run python api_server.py
# → http://localhost:8001

# Terminal 2: Next.js LMS frontend
cd zizi-lms && npm install && npm run dev
# → http://localhost:3000

# Terminal 3: Chainlit chat app (optional)
uv run chainlit run app.py
# → http://localhost:8000
```

### 4. Optional: Warm the Cache

Pre-generate all bytes for all topics (runs in background):

```bash
uv run python scripts/warm_cache.py --force
uv run python scripts/warm_cache.py --modules 03,04 --force  # specific modules
```

---

## Demo Flow

1. Open `http://localhost:3000`
2. Select any topic from the sidebar (or press `M` for the topic drawer)
3. In **Learn** mode:
   - The **Analogy** tab shows the DALL-E image + analogy text
   - Click **Interactive** — the p5.js sketch generates and runs (first time: ~15s)
   - Navigate steps with Next/Prev buttons drawn on the canvas
   - Click **Deep Dive** for the RAG-grounded technical breakdown
4. Switch to **Build** mode — the sketch re-appears, code panel syncs to each step
5. Click "Download Notebook" — get a ready-to-run `.ipynb`
6. Switch to **Share** — generate a LinkedIn post + image
7. Click **Regenerate** — choose from 3 alternative analogies or type your own

---

## Evaluation (RAGAS)

```bash
# Generate synthetic QA pairs from the KB
uv run python evals/synthetic_data_gen.py --size 15

# Evaluate baseline (dense retrieval)
uv run python evals/ragas_baseline.py --delay 1.0

# Evaluate HyDE retrieval
uv run python evals/ragas_hyde.py --delay 1.0
```

Metrics: `faithfulness`, `answer_relevancy`, `context_precision`, `context_recall`

---

## What Makes This Different

**Analogy quality**: Claude Sonnet 4.6 generates simple everyday analogies (think "cookies in a jar", not "GPS recalculating"). Each analogy is auto-evaluated for simplicity, clarity, and memorability — retried with feedback if score < 6. 140 concepts pre-generated and cached.

**SVG interactive widgets**: Every concept gets a Claude Sonnet 4.6-generated SVG animation in a fixed HTML shell. Claude fills in `svg_content`, `steps`, and `animate_fn` as JSON — no truncation risk, guaranteed iframe structure, anime.js transitions always loaded. Pre-cached for all 140 concepts.

**Shared widget state**: The Claude interaction is fetched once from the DB cache and shared between Learn (Interactive tab) and Build mode — same API endpoint, no duplicate generation.

**Grounded at every layer**: Analogy bytes cite source files. Chat answers cite source files with relevance scores. Deep Dive tab shows verbatim course material. Nothing is fabricated.

**Full content pipeline**: From learning a concept → sharing it on LinkedIn, with a DALL-E image, dedup protection, and Qdrant ingestion to prevent future duplicates — all in one click.

---

## Project Structure

```
my-ai-assistant/
├── api_server.py          # FastAPI LMS bridge
├── app.py                 # Chainlit entry point
├── pyproject.toml         # Python deps (uv)
├── docker-compose.yml     # Qdrant
├── src/
│   ├── config.py
│   ├── llm.py
│   ├── agents/
│   │   ├── chat_pipeline.py
│   │   └── content_pipeline.py
│   ├── ingestion/
│   ├── lms/
│   │   ├── analogy_pipeline.py          # LangGraph byte pipeline
│   │   ├── analogy_store.py             # SQLite (analogies + claude_interactions)
│   │   ├── byte_generator.py            # ByteGenerator + analogy suggestions
│   │   ├── claude_interaction_generator.py  # Claude SVG animation generator
│   │   └── learning_path.py
│   ├── memory/
│   ├── retrieval/
│   └── tools/
├── evals/
├── scripts/
├── data/
│   ├── analogies.db              # SQLite cache
│   ├── topic_graph.json          # KG
│   └── courses/                  # Ingested course materials
└── zizi-lms/                     # Next.js 14 frontend
    └── src/
        ├── app/learn/[topicId]/page.tsx
        ├── components/
        │   ├── ByteCardV2.tsx
        │   ├── BuildCard.tsx
        │   ├── InteractivePlayer.tsx
        │   ├── RegeneratePanel.tsx
        │   └── ShareModal.tsx
        ├── lib/api.ts
        ├── store/lmsStore.ts
        └── types/index.ts
```

---

## License

MIT — see [LICENSE](LICENSE)

---

*Zizi Byte — AIE9 Certification Challenge final submission by Preetam*
