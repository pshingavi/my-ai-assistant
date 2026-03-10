# Zizi Byte — AIE9 Certification Challenge Video Script
## Target: ≤ 5 minutes | Loom demo recording

---

### OPENING — 0:00–0:30 (30 sec)

> *[Screen: zizi-lms running at localhost:3000 — the Galaxy page, D3 nodes slowly floating]*

"Hey, I'm Preetam, cohort AIE9.

My certification project is called **Zizi Byte** — 'Learn in bytes, think in leaps.'

Here's the problem I was trying to solve: I'm in this bootcamp, every session is 50 to 200 slides plus Jupyter notebooks. I'd study hard on Thursday, and by Monday, it's gone. Worse — I couldn't connect Week 3's agent loop to Week 11's reranking, even though they're deeply related.

So I built an AI micro-learning platform that transforms those dense course materials into analogy-driven, grounded learning — using almost everything we learned in this cohort."

---

### THE STACK TOUR — 0:30–1:10 (40 sec)

> *[Screen: show the galaxy, hover over a node, pan around]*

"This galaxy you're looking at is a **D3 force-directed knowledge graph** — every node is a course topic, the edges are BUILDS_ON relationships I extracted using a **NetworkX DiGraph**, persisted as JSON. Sessions 3 through 11 are all in here.

The whole thing is powered by:
- A **FastAPI bridge** on port 8001
- A **Next.js 14 LMS** frontend
- A **Qdrant vector database** with about 1,200 chunks from 20 course files
- And a **LangGraph content pipeline** with an agentic dedup decision point

Let me click on a topic and show you what learning looks like."

---

### DEMO PART 1 — BYTE CARD & BUILD MODE — 1:10–2:00 (50 sec)

> *[Click "The Agent Loop" node → /learn page loads → Byte card appears]*

"I click 'The Agent Loop' — the system hits my FastAPI endpoint, which calls the **ByteGenerator**. It retrieves grounding context from Qdrant, then uses GPT-4o-mini to generate an **analogy-first explanation**.

See this — it led with a kitchen analogy, then gave the technical explanation, then told me *why this matters*. All grounded in what Session 3 actually teaches.

Now I'll switch to **Build mode**."

> *[Click Build tab — code snippet appears]*

"Build mode extracts the actual notebook code cells from the course material, pairs them with the markdown explanation, and shows them as a runnable snippet. This is from Session 3's LangGraph primitives notebook — not fabricated, pulled from the actual source."

---

### DEMO PART 2 — NATIVE CHAT — 2:00–3:00 (60 sec)

> *[Navigate to /chat — animated empty state with floating particles]*

"Now this is the part I'm most proud of — the native chat. Full RAG pipeline, fully streaming, built into the LMS.

Let me ask: *'Explain the agent loop like I'm 5'*"

> *[Type and hit enter — watch the pipeline steps animate, then tokens stream in]*

"Watch the pipeline steps animate as they execute — Knowledge Graph retrieval, Cohere reranking, then the answer streams token by token.

Here's what's happening under the hood — this is Sessions 2, 3, 4, 6, and 11 coming together:

1. **KGRetriever** — it embeds the query, finds the closest topic node in the NetworkX graph, traverses BUILDS_ON edges up to 2 hops — multi-hop agentic retrieval from Session 4
2. **DenseRetriever** — runs in parallel, k=15, raw query — baseline from Session 2
3. ALL unique chunks — about 25 of them — are passed to **Cohere Rerank**, which picks the top 8 by neural relevance. This was a critical fix: I was pre-filtering by embedding score, which cut the exact Session 3 PDF before Cohere ever saw it.
4. GPT-4o-mini streams the answer using ONLY what's in the context — the system prompt explicitly forbids answering from pre-trained knowledge.

See the sources at the bottom — `AIE9_Session03_The-Agent-Loop.pdf` with relevance 0.64. Grounded."

---

### DEMO PART 3 — CONTENT CREATOR + DEDUP — 3:00–3:45 (45 sec)

> *[Switch to Chainlit at localhost:8000, type 'create']*

"Chainlit handles the content creator pipeline. I type 'create' and a **LangGraph graph** kicks off:

- **Tavily** searches for trending AI topics — arxiv, OpenAI, HuggingFace
- LLM picks the most interesting one
- **dedup_check_node** — this is the agentic decision point from Session 3 and 4 — it embeds the topic, searches Qdrant for similar past posts, and if cosine similarity exceeds 0.85, it halts the pipeline. No human in the loop.
- If it's novel, Dense retrieval grounds the post in course material, GPT-4o-mini generates a LinkedIn post in Hook→Analogy→Tech→CTA format, and DALL-E 3 generates a matching HD poster.

Let me show the dedup branch firing — I'll create on the same topic twice."

> *[Run create again on same topic — show dedup message]*

"Similarity 0.91 — pipeline halted. That's a real conditional LangGraph edge making a runtime decision."

---

### EVALUATIONS — 3:45–4:20 (35 sec)

> *[Screen: show evals/ folder, then EVALUATION_REPORT.md results table]*

"On evaluations — this is Session 10's RAGAS framework applied:

**Baseline Dense retrieval**: Context Recall 0.59, Faithfulness 0.37.

**HyDE upgrade** — Session 11 — generates a hypothetical answer in the KB's vocabulary, then embeds that. Faithfulness jumped +28% to 0.48. Answer relevancy +33% to 0.52.

I also ran all **7 Module 11 retrieval strategies** on the same 15-sample synthetic golden set: Semantic Chunking wins with composite score 2.261, Naive Dense is 2.237 — just 1.1% behind, validating the 512-char chunking decision.

The eval scripts are all in `evals/` — `ragas_baseline.py`, `ragas_hyde.py`, `ragas_module11.py` — reproducible with one command each."

---

### CLOSING — 4:20–4:50 (30 sec)

> *[Back to Galaxy at localhost:3000]*

"So what you've seen is sessions 2 through 11 assembled into one coherent product:

- Session 2's embeddings power every retrieval
- Session 3's LangGraph StateGraph runs the content pipeline
- Session 4's conditional edges drive the dedup agentic decision
- Session 6's conversation memory keeps 8-turn chat context
- Session 10's RAGAS metrics quantify every retrieval improvement
- Session 11's advanced retrievers are all implemented and benchmarked

The LMS itself is Next.js 14, FastAPI, Qdrant, NetworkX, Cohere — a full-stack AI engineering build.

Thanks for watching. Zizi Byte — learn in bytes, think in leaps."

---

## Recording Tips

- **Total target: 4:45–5:00** — this script runs ~4:50 at a natural speaking pace
- Start with both apps running: `localhost:3000` and `localhost:8000`
- Have Qdrant up and KG ingested before recording
- Demo the chat FIRST on a fresh topic so the streaming animation is clean
- For dedup demo: run `create` once, let it finish, then immediately run `create` again
- Keep terminal visible for a second when switching between ports — it shows the stack is real
- Don't rush the typing — let the SSE streaming animations play naturally, they're the best visual

## Loom Tips

- Record at 1080p, share screen only (no webcam required by challenge)
- Set Loom to HD before recording
- Submit link in the Google Form: https://forms.gle/yxvhpXiaMDUJ28Gv5
