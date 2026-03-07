# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI-powered LinkedIn content creation + Knowledge Graph RAG assistant for Generative AI professionals. AIE9 Certification Challenge submission.

Two modes: **Content Pipeline** (research → dedup → RAG → post + image) and **Chat** (KG RAG Q&A).

## Commands

```bash
# Install
uv sync

# Start Qdrant (required before running app or evals)
docker compose up -d

# Ingest course materials (run once, or after adding new modules)
uv run python scripts/ingest_courses.py
uv run python scripts/ingest_courses.py --dry-run   # list files only
uv run python scripts/ingest_courses.py --modules 04,11

# Start the app
uv run chainlit run app.py
# → http://localhost:8000

# RAGAS evaluation pipeline (in order)
uv run python evals/synthetic_data_gen.py --size 15
uv run python evals/ragas_baseline.py --delay 1.0
uv run python evals/ragas_hyde.py --delay 1.0
```

## Architecture

**Entry point**: `app.py` (Chainlit) — detects intent from message keywords, routes to one of two LangGraph pipelines stored in `cl.user_session`.

**Content pipeline** (`src/agents/content_pipeline.py`): LangGraph graph with nodes: `research → merge_topics → dedup_check →[conditional]→ retrieve_context → generate_post → generate_image → ingest_post`. The `dedup_check_node` is the agentic decision point — branches to `inform_duplicate` if cosine similarity > `DEDUP_THRESHOLD`.

**Chat pipeline** (`src/agents/chat_pipeline.py`): `kg_retrieve → generate_answer`. Uses `KGRetriever` which traverses the topic graph then runs HyDE on each related topic.

**Retrieval stack** (`src/retrieval/`):
- `DenseRetriever` — baseline, embeds raw query
- `HyDERetriever` — generates hypothetical document, embeds that instead (Task 6 advanced)
- `KGRetriever` — KG traversal (NetworkX) + HyDE on related topics (used in chat)
- All implement the `Retriever` protocol from `base.py`

**Memory** (`src/memory/`):
- `qdrant_store.py` — `upsert_chunks()`, `search()`, `get_langchain_retriever()` (used in evals)
- `topic_graph.py` — NetworkX DiGraph persisted as `data/topic_graph.json`; `get_topic_graph()` singleton

**Tools** (`src/tools/`): `tavily_tool.py`, `x_tool.py` (graceful no-op if `X_BEARER_TOKEN` unset), `image_tool.py` (DALL-E 3)

**Ingestion** (`src/ingestion/`): `CourseIngester` handles PDF/notebook/markdown; `PostIngester` stores generated posts + updates KG

**Config**: `src/config.py` — Pydantic Settings, all values from `.env`. `get_settings()` is `@lru_cache`. Call `cfg.configure_langsmith()` early in startup to enable tracing.

## Key Design Decisions

- `src/` is installed as a package via hatchling — imports work as `from src.X import Y` from any script
- LangSmith tracing is **opt-in** — only activates when `LANGCHAIN_API_KEY` is set
- X.com search is **opt-in** — graceful empty list if `X_BEARER_TOKEN` is unset
- RAGAS uses `SingleTurnSample` + `EvaluationDataset` (0.2.x API from AIE9 Session 10 notebook)
- Qdrant collections are auto-created on first upsert via `ensure_collection()`
- Knowledge Graph JSON is stored at `data/topic_graph.json` (auto-created)

## Env Vars

Copy `.env.example` → `.env`. Required: `OPENAI_API_KEY`, `TAVILY_API_KEY`. Optional: `LANGCHAIN_API_KEY`, `X_BEARER_TOKEN`.
