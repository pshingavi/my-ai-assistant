'use client';

import { useState, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  BackgroundVariant,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';

// ─── Types ──────────────────────────────────────────────────────────────────────
interface NodeDetail {
  title: string;
  group: string;
  groupColor: string;
  icon: string;
  what: string;
  why: string;
  usage: string;
  tech: string;
  module?: string;
}

interface ServiceNodeData {
  label: string;
  icon: string;
  subtitle?: string;
  group: string;
  color: string;
  detailKey: string;
  [key: string]: unknown;
}

// ─── Node detail metadata ────────────────────────────────────────────────────────
const NODE_DETAILS: Record<string, NodeDetail> = {
  // ── Entry Points ──
  chainlit: {
    title: 'Chainlit App', group: 'Entry Point', groupColor: '#3b82f6', icon: '⚡',
    what: 'Web-based chat interface at port 8000. Routes user intent to Chat, Content pipeline, or LMS links based on keyword detection.',
    why: 'Provides conversational access to course content without the structured LMS — good for free-form Q&A and content generation.',
    usage: 'uv run chainlit run app.py → http://localhost:8000',
    tech: 'Python, Chainlit 1.x, SSE streaming, async message handlers',
  },
  nextjs: {
    title: 'Next.js LMS', group: 'Entry Point', groupColor: '#3b82f6', icon: '🖥️',
    what: 'Frontend LMS at port 3000. Renders topics, Zizi Bytes (analogy + interactive + deep dive), Build mode, and Share mode.',
    why: 'The primary structured learning experience — users navigate topics → concepts → bytes.',
    usage: 'cd zizi-lms && npm run dev → http://localhost:3000',
    tech: 'Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, Zustand',
  },

  // ── API Layer ──
  fastapi: {
    title: 'FastAPI Server', group: 'API Layer', groupColor: '#7c3aed', icon: '🔌',
    what: 'Bridge between Next.js and all AI pipelines. Exposes JSON REST endpoints for bytes, topics, Claude interactions, notebooks, and share post creation.',
    why: 'Decouples React frontend from Python AI logic. All heavy LLM calls and RAG live server-side.',
    usage: 'uv run python api_server.py → http://localhost:8001',
    tech: 'FastAPI, async/await, aiosqlite, Python 3.11+, CORS for :3000',
  },

  // ── System-view pipeline boxes ──
  'lms-pipe': {
    title: 'Byte Generator', group: 'Byte Generator', groupColor: '#6d28d9', icon: '📚',
    what: 'LangGraph pipeline that generates Zizi Bytes on cache miss: RAG retrieval → Claude analogy → evaluation (retry if <6/10) → DALL-E image → SVG interaction → SQLite persist.',
    why: 'Orchestrates multi-step AI generation with quality gating. Each concept generated once and cached — FastAPI reads from SQLite to serve instantly.',
    usage: 'GET /api/topic/{id}/concept/{c}/claude-interaction triggers on cache miss. POST /p5sketch/regenerate clears and reruns.',
    tech: 'LangGraph, ByteGenerator, ClaudeInteractionGenerator, aiosqlite',
    module: 'Applied: Sessions 03 (LangGraph), 04 (RAG), 07 (Evaluation)',
  },
  'chat-pipe': {
    title: 'Chat Pipeline', group: 'Chat', groupColor: '#4f46e5', icon: '💬',
    what: 'KG+Dense dual retrieval → Cohere Rerank → GPT-4o streaming answer with analogy-first format and source citations.',
    why: 'Every answer grounded in course material. No hallucination — cites the exact source file + relevance score.',
    usage: 'Invoked from app.py when Chainlit intent = Q&A',
    tech: 'LangGraph, KGRetriever, DenseRetriever, Cohere Rerank v3.5, GPT-4o streaming',
    module: 'Applied: Sessions 04 (RAG), 09 (KG), 11 (Reranking)',
  },
  'content-pipe': {
    title: 'LinkedIn Creator', group: 'Content', groupColor: '#059669', icon: '🔄',
    what: 'LangGraph agentic pipeline: research (Tavily+X) → dedup check → RAG context → LinkedIn post (GPT-4o) → DALL-E image → Qdrant ingest to prevent future duplicates.',
    why: 'Full automation from AI topic to publishable LinkedIn content. dedup_check_node is the agentic branching decision point.',
    usage: 'Triggered from Share mode in LMS or Chainlit content creation intent',
    tech: 'LangGraph, Tavily, X.com API, DALL-E 3, cosine dedup (Qdrant), post ingestion',
    module: 'Applied: Sessions 03 (Agentic LangGraph), 04 (RAG), 05 (Tools)',
  },
  'ingest-pipe': {
    title: 'Ingestion Pipeline', group: 'Ingestion', groupColor: '#0891b2', icon: '📥',
    what: 'Offline pipeline that reads course materials (PDFs, Jupyter notebooks, markdown), chunks text, embeds with OpenAI, and upserts to Qdrant. Also builds the NetworkX Knowledge Graph.',
    why: 'Seeds the vector store and KG that all three runtime pipelines (Byte, Chat, Content) depend on.',
    usage: 'uv run python scripts/ingest_courses.py (run once, or after adding new modules)',
    tech: 'CourseIngester, RecursiveCharacterTextSplitter, text-embedding-3-small, Qdrant upsert, NetworkX',
    module: 'Applied: Sessions 04 (Vector Stores), 09 (Knowledge Graphs)',
  },

  // ── Memory ──
  sqlite: {
    title: 'SQLite Cache', group: 'Memory', groupColor: '#d97706', icon: '🗄️',
    what: 'Local DB with two tables: analogies (versioned, is_active flag) and claude_interactions (SVG HTML + steps JSON). FastAPI reads from here on every request to serve bytes without re-generating.',
    why: 'Avoids re-generating expensive LLM outputs. 140 concepts pre-cached, served in <100ms.',
    usage: 'analogy_store.py — get_active_byte(), get_claude_interaction() [reads]; save_claude_interaction(), clear_concept_cache() [writes]',
    tech: 'SQLite, aiosqlite, versioned rows with is_active=1, (topic_id, concept) composite key',
  },
  qdrant: {
    title: 'Qdrant Vector Store', group: 'Memory', groupColor: '#d97706', icon: '🔍',
    what: 'Vector DB storing embedded course chunks (PDFs, notebooks, markdown). Supports cosine similarity ANN search. Also stores generated LinkedIn posts for dedup.',
    why: 'Foundation of RAG — enables semantic search over all ingested course materials.',
    usage: 'docker compose up -d → port 6333. Seeded via scripts/ingest_courses.py',
    tech: 'Qdrant OSS (Docker), text-embedding-3-small (1536-dim), cosine distance',
    module: 'Applied: Session 04 (Vector Databases & RAG)',
  },
  kg: {
    title: 'Knowledge Graph', group: 'Memory', groupColor: '#d97706', icon: '🕸️',
    what: 'NetworkX DiGraph mapping relationships between 140 topics across 11 modules. Enables traversal-based retrieval that dense search alone misses.',
    why: 'Captures cross-module connections — e.g. embeddings → reranking → evaluation.',
    usage: 'topic_graph.py — get_topic_graph() singleton. Persisted at data/topic_graph.json',
    tech: 'NetworkX DiGraph, JSON persistence, module_number node attributes, neighbor traversal',
    module: 'Applied: Session 09 (Knowledge Graphs)',
  },

  // ── AI Services ──
  openai: {
    title: 'OpenAI GPT-4o', group: 'AI Service', groupColor: '#db2777', icon: '🤖',
    what: 'Powers chat answers (streaming), step metadata generation, LinkedIn post creation. text-embedding-3-small provides all vector embeddings.',
    why: 'Best-in-class for long-form grounded generation with streaming support.',
    usage: 'src/llm.py — get_openai_client(). Requires OPENAI_API_KEY.',
    tech: 'GPT-4o, GPT-4o-mini, text-embedding-3-small 1536-dim, stream=True',
  },
  claude: {
    title: 'Claude Sonnet 4.6', group: 'AI Service', groupColor: '#db2777', icon: '🧠',
    what: 'Generates analogy text (with self-evaluation score ≥6/10 gate), SVG interactive animations (JSON-fill into fixed HTML shell), and evaluates analogy quality.',
    why: 'Excels at creative structured output. JSON-fill approach guarantees animation structure without truncation risk.',
    usage: 'ClaudeInteractionGenerator, ByteGenerator. Requires ANTHROPIC_API_KEY.',
    tech: 'claude-sonnet-4-6, structured JSON output, anime.js 3.2 SVG animations',
  },
  cohere: {
    title: 'Cohere Rerank v3.5', group: 'AI Service', groupColor: '#db2777', icon: '⚖️',
    what: 'Cross-encoder reranking of 30 retrieved chunks → top 8 most relevant. Dramatically improves answer quality over bi-encoder alone.',
    why: 'Two-stage retrieval: fast dense gets candidates, Cohere cross-encoder scores true query-chunk relevance.',
    usage: 'chat_pipeline.py — cohere_client.rerank(). Requires COHERE_API_KEY (graceful fallback if unset).',
    tech: 'Cohere Rerank v3.5, cross-encoder, 30→8 compression',
    module: 'Applied: Session 11 (Reranking)',
  },
  tavily: {
    title: 'Tavily + X.com', group: 'Tools', groupColor: '#0891b2', icon: '🔎',
    what: 'Web search (Tavily) + social signals (X/Twitter) to surface trending AI topics for the content pipeline.',
    why: 'Content pipeline needs fresh external signals beyond the static course KB.',
    usage: 'tavily_tool.py, x_tool.py. Requires TAVILY_API_KEY; X_BEARER_TOKEN optional (no-op if unset).',
    tech: 'Tavily API, tweepy X client, parallel tool calls, graceful degradation',
    module: 'Applied: Session 05 (Tools & Agents)',
  },

  // ── LMS Pipeline detail nodes ──
  'topic-sel': {
    title: 'Topic Selection', group: 'Frontend', groupColor: '#3b82f6', icon: '🎯',
    what: 'User clicks a topic in the sidebar or topic drawer. Triggers loadByte() which checks cache or kicks off generation.',
    why: 'Entry point to the learning experience. Topics ordered by module_number 01→11 from the Knowledge Graph.',
    usage: 'TopicSidebar / TopicDrawer → onSelect → router.push(/learn/{topicId})',
    tech: 'Zustand lmsStore, Next.js App Router, KG topic_graph.json nodes list',
  },
  'cache-check': {
    title: 'SQLite Cache Check', group: 'Cache', groupColor: '#d97706', icon: '💾',
    what: 'Checks analogies and claude_interactions tables for an existing active byte for this (topic_id, concept) pair.',
    why: 'Avoids expensive LLM calls for 140 pre-cached concepts. Cache hit serves in <100ms.',
    usage: 'analogy_store.py — get_active_byte(), get_claude_interaction()',
    tech: 'aiosqlite, is_active=1 versioning, (topic_id, concept) composite key',
  },
  'byte-gen': {
    title: 'ByteGenerator', group: 'Generator', groupColor: '#6d28d9', icon: '⚙️',
    what: 'Orchestrates byte generation: RAG retrieval for context → Claude analogy generation → self-evaluation → retry if score <6.',
    why: 'Quality gate — analogies scored on simplicity, clarity, memorability before being saved.',
    usage: 'byte_generator.py — ByteGenerator.generate_byte(topic_id, concept)',
    tech: 'LangGraph analogy_pipeline, DenseRetriever for RAG context, Claude evaluation loop',
    module: 'Applied: Sessions 03 (LangGraph), 04 (RAG), 07 (Eval)',
  },
  'analogy-gen': {
    title: 'Analogy Generator', group: 'Claude', groupColor: '#7c3aed', icon: '✨',
    what: 'Claude Sonnet 4.6 generates a simple everyday analogy for the concept. Auto-evaluated, retried with feedback if score <6/10.',
    why: 'Core value prop — making dense AI concepts accessible via intuitive analogies like "cookies in a jar".',
    usage: 'analogy_pipeline.py — analogy_generator LangGraph node',
    tech: 'Claude Sonnet 4.6, self-evaluation loop, structured scoring prompt',
    module: 'Applied: Session 01 (Prompting), 07 (Evaluation loops)',
  },
  'dalle-img': {
    title: 'DALL-E 3 Image', group: 'Image', groupColor: '#db2777', icon: '🎨',
    what: 'Generates a visual illustration of the analogy. Stored as PNG in zizi-lms/public/generated/images/.',
    why: 'Visual memory aid — the image reinforces the analogy and makes the byte memorable.',
    usage: 'image_tool.py — generate_image(). Served by Next.js as static at /generated/images/',
    tech: 'DALL-E 3, 1024×1024, URL downloaded locally, Next.js static serving',
    module: 'Applied: Session 05 (Multimodal)',
  },
  'claude-svg': {
    title: 'Claude SVG Generator', group: 'Claude', groupColor: '#4f46e5', icon: '🎬',
    what: 'Claude Sonnet 4.6 fills a fixed HTML shell with svg_content, steps[], and animate_fn as JSON. 5 steps with anime.js transitions.',
    why: 'JSON-fill approach guarantees iframe structure without truncation. Pre-cached for all 140 concepts.',
    usage: 'claude_interaction_generator.py — ClaudeInteractionGenerator.generate(topic, concept, analogy)',
    tech: 'Claude Sonnet 4.6, JSON structured output, anime.js 3.2, sandboxed iframe srcdoc',
    module: 'Applied: Session 01 (Structured Output), Session 08 (Claude)',
  },
  'sqlite-save': {
    title: 'SQLite Persist', group: 'Cache', groupColor: '#d97706', icon: '💾',
    what: 'Saves analogy and Claude interaction to SQLite. Marks new row is_active=1, deactivates old versions.',
    why: 'Versioned caching — regeneration preserves history, just activates the new version.',
    usage: 'analogy_store.py — save_byte(), save_claude_interaction()',
    tech: 'aiosqlite, atomic transactions, soft versioning with is_active flag',
  },
  'fastapi-serve': {
    title: 'FastAPI Serve', group: 'API Layer', groupColor: '#7c3aed', icon: '🔌',
    what: 'Returns cached byte JSON and Claude interaction (sketch_code HTML + steps metadata) to the frontend.',
    why: 'Separates generation from serving — frontend always gets fast cached responses.',
    usage: 'GET /api/topic/{id}/concept/{c}/claude-interaction',
    tech: 'FastAPI async endpoint, JSON response with sketch_code + steps array',
  },
  'nextjs-render': {
    title: 'ByteCardV2', group: 'Frontend', groupColor: '#3b82f6', icon: '🖥️',
    what: 'ByteCardV2 renders analogy + image. InteractivePlayer renders SVG animation in sandboxed iframe with theme CSS injection.',
    why: 'The user-facing learning experience — byte comes to life as interactive artifact.',
    usage: 'ByteCardV2.tsx, InteractivePlayer.tsx — srcDoc with light-theme CSS overrides',
    tech: 'React, Framer Motion, sandboxed iframe srcdoc, postMessage for step sync',
  },

  // ── Chat Pipeline ──
  'user-query': {
    title: 'User Query', group: 'Chat', groupColor: '#3b82f6', icon: '💬',
    what: 'User submits question in Chainlit. Intent detected as Q&A, routed to chat_pipeline.run().',
    why: 'Starting point of grounded RAG-based Q&A over all 11 modules of course content.',
    usage: 'app.py — on_message → intent routing → chat_pipeline',
    tech: 'Chainlit async handler, keyword-based intent detection',
  },
  'kg-ret': {
    title: 'KG Retriever', group: 'Retrieval', groupColor: '#4f46e5', icon: '🕸️',
    what: 'Traverses KG to find topics related to the query, then dense-retrieves chunks for those topics. k=15.',
    why: 'Captures cross-module connections pure dense search misses — query about "evaluation" retrieves RAGAS, LangSmith, and evals modules.',
    usage: 'retrieval/kg_retriever.py — KGRetriever.retrieve(query)',
    tech: 'NetworkX neighbor traversal + DenseRetriever on related topic chunks',
    module: 'Applied: Session 09 (Knowledge Graphs)',
  },
  'dense-ret': {
    title: 'Dense Retriever', group: 'Retrieval', groupColor: '#6d28d9', icon: '🔍',
    what: 'Embeds raw query with text-embedding-3-small, retrieves top-k=15 semantically similar chunks from Qdrant.',
    why: 'Fast semantic baseline. Combined with KG retrieval for broader coverage (30 total candidates for Cohere).',
    usage: 'retrieval/dense_retriever.py — DenseRetriever.retrieve(query)',
    tech: 'OpenAI text-embedding-3-small, Qdrant cosine ANN search, k=15',
    module: 'Applied: Session 04 (Dense Retrieval & Embeddings)',
  },
  'cohere-rank': {
    title: 'Cohere Rerank', group: 'Reranking', groupColor: '#db2777', icon: '⚖️',
    what: 'Cross-encoder reranking of all unique KG+Dense chunks (up to 30) → top 8 most relevant to the query.',
    why: 'Bi-encoder retrieval is fast but imprecise. Cohere cross-encoder scores true query-chunk relevance directly.',
    usage: 'chat_pipeline.py — cohere_client.rerank(query, documents, top_n=8)',
    tech: 'Cohere Rerank v3.5, cross-encoder, 30→8 compression',
    module: 'Applied: Session 11 (Reranking)',
  },
  'gpt4o-gen': {
    title: 'GPT-4o Stream', group: 'Generation', groupColor: '#059669', icon: '🤖',
    what: 'Generates streaming answer grounded in top-8 reranked chunks. Analogy-first format, cites source files.',
    why: 'Streaming gives immediate feedback. Analogy-first makes technical answers digestible. Citations build trust.',
    usage: 'chat_pipeline.py — openai.chat.completions.create(stream=True)',
    tech: 'GPT-4o, streaming SSE via Chainlit, system prompt with analogy + citation instructions',
  },
  'chat-response': {
    title: 'Response + Citations', group: 'Chat', groupColor: '#3b82f6', icon: '📝',
    what: 'Final answer: analogy → technical explanation → source file citations with relevance scores. 8-turn conversation memory.',
    why: 'Every claim traceable to a course file. Relevance scores help user judge source quality.',
    usage: 'Rendered in Chainlit with source citation cards below the main answer',
    tech: 'Chainlit UI, conversation history buffer (8 turns), relevance score display',
    module: 'Applied: Session 07 (Eval & Grounding), 06 (Memory)',
  },

  // ── Content Pipeline ──
  research: {
    title: 'Research Node', group: 'Content', groupColor: '#0891b2', icon: '🔎',
    what: 'Parallel Tavily web search + X.com trending search for AI topics. Returns raw research results from both sources.',
    why: 'Content pipeline needs fresh external signals beyond the static course KB.',
    usage: 'content_pipeline.py — research LangGraph node → tavily_tool + x_tool',
    tech: 'Tavily API, tweepy X client, parallel async tool calls',
    module: 'Applied: Session 05 (Tools)',
  },
  merge: {
    title: 'Merge Topics', group: 'Content', groupColor: '#d97706', icon: '🔀',
    what: 'Deduplicates and merges research results from Tavily and X into a clean topic candidate list.',
    why: 'Two sources return overlapping results. Merging prevents generating content about the same topic twice in one session.',
    usage: 'content_pipeline.py — merge_topics LangGraph node',
    tech: 'LangGraph node, string normalization, list deduplication',
  },
  dedup: {
    title: 'Dedup Check', group: 'Decision', groupColor: '#db2777', icon: '🚦',
    what: 'Embeds proposed topic, checks cosine similarity vs all ingested posts in Qdrant. Branches: duplicate or new.',
    why: 'Prevents near-duplicate content generation. This is the agentic decision point in the LangGraph.',
    usage: 'content_pipeline.py — dedup_check_node. Conditional edge: inform_duplicate | retrieve_context',
    tech: 'OpenAI embeddings, Qdrant cosine similarity, DEDUP_THRESHOLD config var',
    module: 'Applied: Session 03 (Agentic Branching), 04 (Embeddings)',
  },
  'inform-dup': {
    title: 'Inform Duplicate', group: 'Terminal', groupColor: '#f59e0b', icon: '⚠️',
    what: 'Terminal node for duplicate branch. Returns message informing user the topic was already covered recently.',
    why: 'Graceful handling — user is informed rather than producing near-duplicate content.',
    usage: 'content_pipeline.py — inform_duplicate node (terminal, no outgoing edges)',
    tech: 'LangGraph terminal node, conditional edge from dedup_check_node',
  },
  'ret-ctx': {
    title: 'Retrieve Context', group: 'Retrieval', groupColor: '#6d28d9', icon: '📖',
    what: 'RAG retrieval over the course KB for the proposed topic. Provides grounding context for post generation.',
    why: 'LinkedIn posts about AI should reference actual course knowledge, not hallucinated content.',
    usage: 'content_pipeline.py — retrieve_context node → DenseRetriever k=5',
    tech: 'DenseRetriever k=5, Qdrant semantic search, chunk formatting',
    module: 'Applied: Session 04 (RAG)',
  },
  'gen-post': {
    title: 'Generate Post', group: 'Generation', groupColor: '#059669', icon: '✍️',
    what: 'GPT-4o generates LinkedIn post grounded in retrieved course context. Includes ZiziByte attribution.',
    why: 'Combines external research signal with internal course knowledge for credible, grounded posts.',
    usage: 'content_pipeline.py — generate_post node',
    tech: 'GPT-4o, LinkedIn formatting guidelines in system prompt, ~280-word target',
  },
  'gen-img': {
    title: 'Generate Image', group: 'Image', groupColor: '#db2777', icon: '🎨',
    what: 'DALL-E 3 generates a visual for the LinkedIn post based on topic and post content.',
    why: 'LinkedIn posts with images get significantly higher engagement.',
    usage: 'content_pipeline.py — generate_image node → image_tool.generate_image()',
    tech: 'DALL-E 3, 1024×1024, URL → downloaded to public/',
    module: 'Applied: Session 05 (Multimodal Tools)',
  },
  ingest: {
    title: 'Ingest Post', group: 'Vector Store', groupColor: '#d97706', icon: '📥',
    what: 'Embeds and upserts generated post into Qdrant. Updates Knowledge Graph with new topic node.',
    why: 'Closes the feedback loop — generated posts join the KB, preventing near-duplicate generation in future.',
    usage: 'content_pipeline.py — ingest_post node → PostIngester',
    tech: 'PostIngester, Qdrant upsert, NetworkX KG update, data/topic_graph.json persist',
    module: 'Applied: Sessions 04 (Vector Stores), 09 (KG update)',
  },

  // ── Ingestion Pipeline ──
  'course-files': {
    title: 'Course Materials', group: 'Source', groupColor: '#0891b2', icon: '📂',
    what: 'Raw AIE9 course materials: PDF slide decks (Session01–11), Jupyter notebooks (.ipynb), and markdown files stored in data/courses/.',
    why: 'The knowledge base that powers all RAG retrieval — every grounded answer and deep dive traces back to these files.',
    usage: 'Place files in data/courses/ then run scripts/ingest_courses.py',
    tech: 'PDFs (50–200 slides each), .ipynb notebooks, .md files — all parsed by CourseIngester',
    module: 'Applied: Sessions 01–11 course content',
  },
  ingester: {
    title: 'CourseIngester', group: 'Ingestion', groupColor: '#0891b2', icon: '⚙️',
    what: 'Reads each file type (PDF via PyMuPDF, notebooks via nbformat, markdown as-is), extracts raw text, and hands off to the chunker.',
    why: 'Single entry point for all file types — consistent chunking and metadata tagging regardless of source format.',
    usage: 'src/ingestion/course_ingester.py — CourseIngester.ingest(file_path)',
    tech: 'PyMuPDF (fitz), nbformat, plain text extraction, module_number tagging from filename',
    module: 'Applied: Session 04 (Document Ingestion)',
  },
  chunker: {
    title: 'Text Chunker', group: 'Ingestion', groupColor: '#6d28d9', icon: '✂️',
    what: 'Splits extracted text into overlapping chunks with RecursiveCharacterTextSplitter. Preserves sentence boundaries.',
    why: 'Chunks must fit in embedding context window and be semantically coherent. Overlap ensures no context is lost at boundaries.',
    usage: 'chunk_size=1000, chunk_overlap=200, preserving source metadata',
    tech: 'LangChain RecursiveCharacterTextSplitter, chunk_size=1000, overlap=200',
    module: 'Applied: Session 04 (Chunking Strategies)',
  },
  embedder: {
    title: 'OpenAI Embedder', group: 'Embedding', groupColor: '#db2777', icon: '🔢',
    what: 'Embeds each chunk with text-embedding-3-small (1536-dim). Batched for rate limit safety.',
    why: 'Dense vector representation enables semantic similarity search at query time.',
    usage: 'src/memory/qdrant_store.py — upsert_chunks() calls OpenAI embeddings API',
    tech: 'OpenAI text-embedding-3-small, 1536-dim, batched requests, cosine distance',
    module: 'Applied: Session 04 (Embeddings & Vector Stores)',
  },
  'qdrant-up': {
    title: 'Qdrant Upsert', group: 'Vector Store', groupColor: '#d97706', icon: '🔍',
    what: 'Upserts embedded chunk vectors into Qdrant collection course_knowledge_base. Auto-creates collection on first run.',
    why: 'Persists vectors for ANN search at runtime. ensure_collection() handles idempotent setup.',
    usage: 'qdrant_store.py — upsert_chunks(chunks, collection). docker compose up -d first.',
    tech: 'Qdrant OSS (Docker :6333), PointStruct upsert, payload metadata (source, content)',
    module: 'Applied: Session 04 (Qdrant & Vector DBs)',
  },
  'kg-build': {
    title: 'KG Builder', group: 'Knowledge Graph', groupColor: '#059669', icon: '🕸️',
    what: 'Builds a NetworkX DiGraph from topic metadata extracted during ingestion. Nodes = topics, edges = relationships between modules. Persisted as JSON.',
    why: 'Enables graph-based retrieval that bridges cross-module concepts — embeddings → reranking → RAGAS evaluation.',
    usage: 'topic_graph.py — build_topic_graph(), persisted to data/topic_graph.json',
    tech: 'NetworkX DiGraph, JSON persistence, module_number attributes, neighbor traversal for KGRetriever',
    module: 'Applied: Session 09 (Knowledge Graphs)',
  },
};

// ─── Helper: node ─────────────────────────────────────────────────────────────────
function n(
  id: string, label: string, icon: string, group: string, color: string,
  x: number, y: number, subtitle?: string, detailKey?: string,
): Node<ServiceNodeData> {
  return {
    id, type: 'service', position: { x, y },
    data: { label, icon, group, color, subtitle, detailKey: detailKey ?? id },
  };
}

// ─── Helper: edge ─────────────────────────────────────────────────────────────────
function e(
  id: string, source: string, target: string, color: string, label?: string,
): Edge {
  return {
    id, source, target,
    animated: true,
    style: { stroke: color, strokeWidth: 2, opacity: 0.75 },
    markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
    ...(label ? {
      label,
      labelStyle: { fontSize: 9, fill: color, fontWeight: 700, fontFamily: 'Inter, sans-serif' },
      labelBgStyle: { fill: '#fefeff', fillOpacity: 0.95 },
      labelBgPadding: [4, 6] as [number, number],
      labelBgBorderRadius: 4,
    } : {}),
  };
}

// ─── Diagrams ─────────────────────────────────────────────────────────────────────
//
// Layout strategy per diagram:
//   system  — 5 horizontal rows, each layer clearly separated by 180px vertically
//   lms     — left-to-right main path; generation fork fans below then rejoins
//   chat    — left-to-right linear with parallel retrieval fork at start
//   content — left-to-right linear with conditional branch splitting up/down at dedup
//   ingest  — left-to-right linear pipeline, KG branch splits downward at end
//
const DIAGRAMS: Record<string, { nodes: Node<ServiceNodeData>[]; edges: Edge[] }> = {

  // ── System Overview ──────────────────────────────────────────────────────────
  // Row 0 (y=0):   Entry points
  // Row 1 (y=180): API + Ingestion (offline)
  // Row 2 (y=360): Runtime pipelines (Byte, Chat, Content)
  // Row 3 (y=540): Memory stores
  // Row 4 (y=720): AI services + Tools
  system: {
    nodes: [
      // Entry points — centred over fastapi
      n('chainlit',      'Chainlit',          '⚡', 'Entry Point',    '#3b82f6', 100, 0,   ':8000'),
      n('nextjs',        'Next.js LMS',       '🖥️', 'Entry Point',    '#3b82f6', 400, 0,   ':3000'),
      // API layer
      n('fastapi',       'FastAPI',           '🔌', 'API Layer',      '#7c3aed', 250, 180, ':8001'),
      // Pipelines — evenly spaced under fastapi
      n('lms-pipe',      'Byte Generator',    '📚', 'Byte Generator', '#6d28d9', 0,   360, 'cache miss → gen'),
      n('chat-pipe',     'Chat Pipeline',     '💬', 'Chat',           '#4f46e5', 250, 360, 'KG+Dense → Cohere'),
      n('content-pipe',  'LinkedIn Creator',  '🔄', 'Content',        '#059669', 510, 360, 'research→dedup→post'),
      // Memory — directly under their primary pipeline
      n('sqlite',        'SQLite',            '🗄️', 'Memory',         '#d97706', 0,   540, 'analogies.db'),
      n('qdrant',        'Qdrant',            '🔍', 'Memory',         '#d97706', 250, 540, ':6333 Docker'),
      n('kg',            'Knowledge Graph',   '🕸️', 'Memory',         '#d97706', 510, 540, 'NetworkX DiGraph'),
      // AI services + tools — spread across bottom
      n('openai',        'OpenAI GPT-4o',     '🤖', 'AI Service',     '#db2777', 0,   720, 'gen + embed'),
      n('claude',        'Claude Sonnet 4.6', '🧠', 'AI Service',     '#db2777', 220, 720, 'analogy + SVG'),
      n('cohere',        'Cohere Rerank',     '⚖️', 'AI Service',     '#db2777', 450, 720, 'v3.5 (30→8)'),
      n('tavily',        'Tavily + X.com',    '🔎', 'Tools',          '#0891b2', 680, 720, 'research'),
    ],
    edges: [
      // Entry → API
      e('e-cl-api',        'chainlit',     'fastapi',      '#3b82f6', 'HTTP'),
      e('e-nx-api',        'nextjs',       'fastapi',      '#3b82f6', 'HTTP'),
      // API → pipelines
      e('e-api-lms',       'fastapi',      'lms-pipe',     '#7c3aed'),
      e('e-api-chat',      'fastapi',      'chat-pipe',    '#7c3aed'),
      e('e-api-content',   'fastapi',      'content-pipe', '#7c3aed'),
      // Byte Generator ↔ SQLite (write then read back)
      e('e-lms-sqlite',    'lms-pipe',     'sqlite',       '#6d28d9', 'write cache'),
      e('e-sqlite-api',    'sqlite',       'fastapi',      '#d97706', 'serve cache'),
      // Byte Generator → AI
      e('e-lms-openai',    'lms-pipe',     'openai',       '#6d28d9', 'DALL-E 3'),
      e('e-lms-claude',    'lms-pipe',     'claude',       '#6d28d9', 'SVG + analogy'),
      // Chat → Memory + AI
      e('e-chat-qdrant',   'chat-pipe',    'qdrant',       '#4f46e5', 'dense search'),
      e('e-chat-kg',       'chat-pipe',    'kg',           '#4f46e5', 'KG traverse'),
      e('e-chat-openai',   'chat-pipe',    'openai',       '#4f46e5', 'stream'),
      e('e-chat-cohere',   'chat-pipe',    'cohere',       '#4f46e5', 'rerank'),
      // Content → Memory + AI + Tools
      e('e-content-qdrant','content-pipe', 'qdrant',       '#059669', 'dedup + ingest'),
      e('e-content-kg',    'content-pipe', 'kg',           '#059669', 'KG update'),
      e('e-content-openai','content-pipe', 'openai',       '#059669', 'post + image'),
      e('e-content-tavily','content-pipe', 'tavily',       '#059669', 'research'),
    ],
  },

  // ── Byte Generator (LMS) Pipeline ────────────────────────────────────────────
  // Main path flows left→right across y=120.
  // On cache miss, ByteGenerator forks:
  //   upper fork (y=30): analogy-gen → dalle-img
  //   lower fork (y=210): claude-svg
  // Both forks converge at sqlite-save (y=120), then continue right.
  lms: {
    nodes: [
      n('topic-sel',     'Topic Selection', '🎯', 'Frontend',   '#3b82f6', 0,    120, 'sidebar click'),
      n('cache-check',   'Cache Check',     '💾', 'Cache',      '#d97706', 220,  120, 'hit or miss?'),
      n('byte-gen',      'ByteGenerator',   '⚙️', 'Generator',  '#6d28d9', 460,  120, 'LangGraph + eval'),
      n('analogy-gen',   'Analogy Gen',     '✨', 'Claude',     '#7c3aed', 700,  20,  'Claude + eval loop'),
      n('dalle-img',     'DALL-E 3',        '🎨', 'Image',      '#db2777', 940,  20,  '1024×1024'),
      n('claude-svg',    'Claude SVG',      '🎬', 'Claude',     '#4f46e5', 700,  220, 'anime.js 5 steps'),
      n('sqlite-save',   'Persist Cache',   '💾', 'Cache',      '#d97706', 1140, 120, 'versioned save'),
      n('fastapi-serve', 'FastAPI',         '🔌', 'API Layer',  '#7c3aed', 1360, 120, 'JSON endpoint'),
      n('nextjs-render', 'ByteCardV2',      '🖥️', 'Frontend',   '#3b82f6', 1590, 120, 'iframe + theme'),
    ],
    edges: [
      e('e-ts-cc',   'topic-sel',    'cache-check',   '#3b82f6', 'lookup'),
      // Cache hit: skip generation entirely
      e('e-cc-hit',  'cache-check',  'fastapi-serve', '#d97706', 'cache hit ⚡'),
      // Cache miss: go to ByteGenerator, fork into analogy and SVG in parallel
      e('e-cc-bg',   'cache-check',  'byte-gen',      '#6d28d9', 'cache miss'),
      e('e-bg-ag',   'byte-gen',     'analogy-gen',   '#7c3aed'),
      e('e-bg-cs',   'byte-gen',     'claude-svg',    '#4f46e5'),
      // Analogy → DALL-E → converge at SQLite
      e('e-ag-di',   'analogy-gen',  'dalle-img',     '#db2777', 'image prompt'),
      e('e-di-ss',   'dalle-img',    'sqlite-save',   '#d97706', 'analogy + img'),
      // Claude SVG → converge at SQLite
      e('e-cs-ss',   'claude-svg',   'sqlite-save',   '#d97706', 'HTML + steps'),
      // Continue to API and render
      e('e-ss-fs',   'sqlite-save',  'fastapi-serve', '#7c3aed', 'cached JSON'),
      e('e-fs-nr',   'fastapi-serve','nextjs-render',  '#3b82f6', 'HTTP response'),
    ],
  },

  // ── Chat Pipeline ─────────────────────────────────────────────────────────────
  // Strictly left→right. Query fans into two parallel retrievers (y=20 / y=180),
  // converges at Cohere, then continues linearly to output.
  chat: {
    nodes: [
      n('user-query',   'User Query',          '💬', 'Chat',      '#3b82f6', 0,   100, 'Chainlit input'),
      n('kg-ret',       'KG Retriever',        '🕸️', 'Retrieval', '#4f46e5', 240, 20,  'NetworkX + dense k=15'),
      n('dense-ret',    'Dense Retriever',     '🔍', 'Retrieval', '#6d28d9', 240, 180, 'Qdrant k=15'),
      n('cohere-rank',  'Cohere Rerank',       '⚖️', 'Reranking', '#db2777', 500, 100, '30 → top 8'),
      n('gpt4o-gen',    'GPT-4o Stream',       '🤖', 'Generation','#059669', 740, 100, 'analogy-first'),
      n('chat-response','Response + Citations','📝', 'Chat',      '#3b82f6', 990, 100, '8-turn memory'),
    ],
    edges: [
      e('e-uq-kg', 'user-query',  'kg-ret',       '#4f46e5', 'query'),
      e('e-uq-dr', 'user-query',  'dense-ret',    '#6d28d9', 'query'),
      e('e-kg-cr', 'kg-ret',      'cohere-rank',  '#4f46e5', '15 chunks'),
      e('e-dr-cr', 'dense-ret',   'cohere-rank',  '#6d28d9', '15 chunks'),
      e('e-cr-g4', 'cohere-rank', 'gpt4o-gen',    '#db2777', 'top 8'),
      e('e-g4-cr2','gpt4o-gen',   'chat-response','#059669', 'stream'),
    ],
  },

  // ── Content (LinkedIn Creator) Pipeline ───────────────────────────────────────
  // Left→right. At dedup, branch splits: duplicate goes up (y=10), new topic goes
  // down (y=210) and continues through the generation chain.
  content: {
    nodes: [
      n('research',   'Research',        '🔎', 'Content',   '#0891b2', 0,    110, 'Tavily + X.com'),
      n('merge',      'Merge Topics',    '🔀', 'Content',   '#d97706', 230,  110, 'dedup candidates'),
      n('dedup',      'Dedup Check',     '🚦', 'Decision',  '#db2777', 470,  110, 'cosine > threshold?'),
      n('inform-dup', 'Inform Duplicate','⚠️', 'Terminal',  '#f59e0b', 710,  10,  'already covered'),
      n('ret-ctx',    'Retrieve Context','📖', 'Retrieval', '#6d28d9', 710,  210, 'RAG k=5'),
      n('gen-post',   'Generate Post',   '✍️', 'Generation','#059669', 960,  210, 'GPT-4o grounded'),
      n('gen-img',    'Generate Image',  '🎨', 'Image',     '#db2777', 1210, 210, 'DALL-E 3'),
      n('ingest',     'Ingest to Qdrant','📥', 'Vector Store','#d97706',1460, 210, '+ KG update'),
    ],
    edges: [
      e('e-r-m',   'research',  'merge',      '#0891b2'),
      e('e-m-d',   'merge',     'dedup',      '#d97706', 'embedded topics'),
      e('e-d-id',  'dedup',     'inform-dup', '#f59e0b', 'duplicate ⚡'),
      e('e-d-rc',  'dedup',     'ret-ctx',    '#6d28d9', 'new topic ✓'),
      e('e-rc-gp', 'ret-ctx',   'gen-post',   '#059669', 'context chunks'),
      e('e-gp-gi', 'gen-post',  'gen-img',    '#db2777', 'post text'),
      e('e-gi-in', 'gen-img',   'ingest',     '#d97706', 'post + image'),
    ],
  },

  // ── Ingestion Pipeline ────────────────────────────────────────────────────────
  // Left→right main path. At Qdrant upsert, a branch splits downward to KG builder.
  ingest: {
    nodes: [
      n('course-files', 'Course Materials',  '📂', 'Source',        '#0891b2', 0,    100, 'PDFs · ipynb · md'),
      n('ingester',     'CourseIngester',    '⚙️', 'Ingestion',     '#0891b2', 240,  100, 'extract text'),
      n('chunker',      'Text Chunker',      '✂️', 'Ingestion',     '#6d28d9', 490,  100, 'size=1000 overlap=200'),
      n('embedder',     'OpenAI Embedder',   '🔢', 'Embedding',     '#db2777', 740,  100, 'text-embedding-3-small'),
      n('qdrant-up',    'Qdrant Upsert',     '🔍', 'Vector Store',  '#d97706', 1000, 100, 'course_knowledge_base'),
      n('kg-build',     'KG Builder',        '🕸️', 'Knowledge Graph','#059669', 1000, 290, 'topic_graph.json'),
    ],
    edges: [
      e('e-cf-ig',  'course-files', 'ingester',  '#0891b2', 'read files'),
      e('e-ig-ch',  'ingester',     'chunker',   '#6d28d9', 'raw text'),
      e('e-ch-em',  'chunker',      'embedder',  '#db2777', 'chunks'),
      e('e-em-qu',  'embedder',     'qdrant-up', '#d97706', '1536-dim vectors'),
      e('e-qu-kg',  'qdrant-up',    'kg-build',  '#059669', 'topic metadata'),
    ],
  },
};

// ─── Custom ServiceNode ───────────────────────────────────────────────────────────
function ServiceNode({ data, selected }: NodeProps) {
  const d = data as ServiceNodeData;
  return (
    <div style={{ position: 'relative' }}>
      <Handle type="target" position={Position.Top}   style={{ opacity: 0, width: 6, height: 6 }} />
      <Handle type="target" position={Position.Left}  style={{ opacity: 0, width: 6, height: 6 }} />
      <div
        style={{
          background: selected ? `${d.color}12` : '#ffffff',
          border: `2px solid ${selected ? d.color : `${d.color}45`}`,
          borderRadius: 14,
          padding: '11px 15px',
          minWidth: 152,
          cursor: 'pointer',
          boxShadow: selected
            ? `0 0 0 3px ${d.color}30, 0 6px 24px rgba(0,0,0,0.12)`
            : '0 2px 12px rgba(0,0,0,0.07)',
          transition: 'all 0.2s ease',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 10, flexShrink: 0,
            background: `${d.color}18`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 17,
          }}>
            {d.icon}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 12, color: '#1e1b4b', lineHeight: 1.3, whiteSpace: 'nowrap' }}>
              {d.label}
            </div>
            {d.subtitle && (
              <div style={{ fontSize: 10, color: '#6b7280', marginTop: 2, whiteSpace: 'nowrap' }}>{d.subtitle}</div>
            )}
          </div>
        </div>
        <div style={{
          marginTop: 9,
          display: 'inline-flex', alignItems: 'center',
          fontSize: 9, fontWeight: 700,
          padding: '2px 8px', borderRadius: 20,
          background: `${d.color}14`, color: d.color,
          letterSpacing: '0.05em', textTransform: 'uppercase',
        }}>
          {d.group}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Right}  style={{ opacity: 0, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

// ─── Detail Panel ─────────────────────────────────────────────────────────────────
function DetailPanel({ detail, onClose }: { detail: NodeDetail; onClose: () => void }) {
  const sections = [
    { label: '🎯 What It Does',   content: detail.what,   mono: false },
    { label: '💡 Why It\'s Here', content: detail.why,    mono: false },
    { label: '🔧 How It\'s Used', content: detail.usage,  mono: true },
    { label: '⚙️ Tech Details',   content: detail.tech,   mono: false },
    ...(detail.module ? [{ label: '🎓 AIE9 Application', content: detail.module, mono: false }] : []),
  ];

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 30, stiffness: 300 }}
      style={{
        position: 'absolute', top: 0, right: 0, bottom: 0, width: 340,
        background: '#ffffff',
        borderLeft: '1px solid rgba(124,58,237,0.1)',
        boxShadow: '-8px 0 40px rgba(0,0,0,0.08)',
        zIndex: 1000,
        display: 'flex', flexDirection: 'column',
        overflowY: 'auto',
      }}
    >
      {/* Header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid rgba(124,58,237,0.08)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 46, height: 46, borderRadius: 13,
              background: `${detail.groupColor}15`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 24, flexShrink: 0,
            }}>
              {detail.icon}
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 14, color: '#1e1b4b', lineHeight: 1.3 }}>{detail.title}</div>
              <div style={{
                fontSize: 10, fontWeight: 700, color: detail.groupColor,
                background: `${detail.groupColor}15`,
                padding: '2px 8px', borderRadius: 20,
                display: 'inline-block', marginTop: 5,
                letterSpacing: '0.06em', textTransform: 'uppercase',
              }}>
                {detail.group}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              fontSize: 16, color: '#9ca3af', background: 'none', border: 'none',
              cursor: 'pointer', padding: '4px 6px', borderRadius: 6, flexShrink: 0, lineHeight: 1,
            }}
            onMouseEnter={e => (e.currentTarget.style.color = '#6b7280')}
            onMouseLeave={e => (e.currentTarget.style.color = '#9ca3af')}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Sections */}
      <div style={{ padding: '16px 20px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        {sections.map((s) => (
          <div key={s.label}>
            <div style={{ fontSize: 10, fontWeight: 800, color: detail.groupColor, marginBottom: 7, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              {s.label}
            </div>
            <div style={{
              fontSize: 12.5, lineHeight: 1.7, color: '#374151',
              ...(s.mono ? {
                background: `${detail.groupColor}08`,
                padding: '9px 12px', borderRadius: 8,
                fontFamily: 'ui-monospace, monospace', fontSize: 11.5,
                borderLeft: `3px solid ${detail.groupColor}40`,
              } : {}),
            }}>
              {s.content}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid rgba(124,58,237,0.08)', marginTop: 'auto', flexShrink: 0 }}>
        <p style={{ fontSize: 10, color: '#9ca3af', textAlign: 'center' }}>
          Click the canvas to close · Click any node to explore
        </p>
      </div>
    </motion.div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────────
interface Props { diagramId: string }

export default function ArchitectureFlow({ diagramId }: Props) {
  const diagram = DIAGRAMS[diagramId] ?? DIAGRAMS.system;
  const [nodes, , onNodesChange] = useNodesState(diagram.nodes);
  const [edges, , onEdgesChange] = useEdgesState(diagram.edges);
  const [selectedDetail, setSelectedDetail] = useState<NodeDetail | null>(null);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const key = (node.data as ServiceNodeData).detailKey;
    setSelectedDetail(NODE_DETAILS[key] ?? null);
  }, []);

  const onPaneClick = useCallback(() => setSelectedDetail(null), []);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.25}
        maxZoom={2}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} color="rgba(124,58,237,0.15)" />
        <Controls style={{
          display: 'flex', flexDirection: 'column', gap: 2,
          background: '#fff', border: '1px solid rgba(124,58,237,0.12)',
          borderRadius: 10, overflow: 'hidden',
          boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
        }} />
        <MiniMap
          nodeColor={(node) => (node.data as ServiceNodeData)?.color ?? '#7c3aed'}
          maskColor="rgba(248,247,255,0.85)"
          style={{ background: '#f8f7ff', border: '1px solid rgba(124,58,237,0.12)', borderRadius: 10 }}
        />
      </ReactFlow>

      {/* Hint */}
      <AnimatePresence>
        {!selectedDetail && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ delay: 0.5 }}
            style={{
              position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)',
              background: 'rgba(124,58,237,0.08)',
              border: '1px solid rgba(124,58,237,0.15)',
              borderRadius: 20, padding: '6px 16px',
              fontSize: 11, color: '#7c3aed', fontWeight: 600,
              pointerEvents: 'none', whiteSpace: 'nowrap',
            }}
          >
            ✦ Click any node to explore details
          </motion.div>
        )}
      </AnimatePresence>

      {/* Detail panel */}
      <AnimatePresence>
        {selectedDetail && (
          <DetailPanel detail={selectedDetail} onClose={() => setSelectedDetail(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}
