"""Module 11 — Comprehensive evaluation of all advanced retrieval strategies.

Tests all 7 strategies from AIE9 Session 11 against the synthetic testset:
  1. Naive (Dense Vector) — baseline
  2. BM25              — sparse keyword retrieval
  3. Multi-Query       — LLM-generated query variants
  4. Parent-Document   — small-to-big context expansion
  5. Contextual Compression (Cohere Rerank v3.5) — requires COHERE_API_KEY
  6. Ensemble          — BM25 + Dense with Reciprocal Rank Fusion
  7. Semantic Chunking — SemanticChunker (percentile) + naive dense retrieval

Each strategy is evaluated on: Context Recall · Faithfulness · Answer Relevancy

Usage:
    uv run python evals/ragas_module11.py
    uv run python evals/ragas_module11.py --delay 2.0 --skip rerank
    uv run python evals/ragas_module11.py --only naive,bm25,ensemble
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

TESTSET_PATH = Path("evals/data/testset.json")
RESULTS_DIR = Path("evals/results")
MODULE11_RESULTS_PATH = RESULTS_DIR / "module11_results.json"

# Strategies available — ordered as in the notebook
ALL_STRATEGIES = [
    "naive",
    "bm25",
    "multi_query",
    "parent_doc",
    "rerank",
    "ensemble",
    "semantic",
]

RAG_PROMPT = (
    "You are a helpful assistant. Use the context provided below to answer the question. "
    "If you do not know the answer, or are unsure, say you don't know.\n\n"
    "Context:\n{context}\n\nQuestion: {question}"
)


# ── Retriever factory ─────────────────────────────────────────────────────────

async def get_retriever(name: str):
    """Return the retriever instance for a given strategy name."""
    if name == "naive":
        from src.retrieval.dense_retriever import DenseRetriever
        return DenseRetriever()
    elif name == "bm25":
        from src.retrieval.bm25_retriever import BM25Retriever
        return BM25Retriever()
    elif name == "multi_query":
        from src.retrieval.multi_query_retriever import MultiQueryRetriever
        return MultiQueryRetriever()
    elif name == "parent_doc":
        from src.retrieval.parent_doc_retriever import ParentDocRetriever
        return ParentDocRetriever()
    elif name == "rerank":
        from src.retrieval.rerank_retriever import RerankRetriever
        return RerankRetriever()
    elif name == "ensemble":
        from src.retrieval.ensemble_retriever import EnsembleRetriever
        return EnsembleRetriever()
    elif name == "semantic":
        from src.retrieval.semantic_chunking_retriever import SemanticChunkingRetriever
        return SemanticChunkingRetriever()
    else:
        raise ValueError(f"Unknown strategy: {name}")


# ── Single-sample RAG ─────────────────────────────────────────────────────────

async def run_rag_for_sample(
    question: str, retriever_name: str, k: int
) -> tuple[str, list[str]]:
    from src.llm import get_async_openai
    from src.config import get_settings

    retriever = await get_retriever(retriever_name)
    chunks = await retriever.retrieve(question, k=k)
    context_str = "\n\n".join(c.content for c in chunks)
    retrieved_contexts = [c.content for c in chunks]

    cfg = get_settings()
    client = get_async_openai()
    prompt = RAG_PROMPT.format(context=context_str, question=question)
    response = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0,
    )
    answer = response.choices[0].message.content or ""
    return answer, retrieved_contexts


# ── Full strategy evaluation ──────────────────────────────────────────────────

async def evaluate_strategy(
    testset: list[dict],
    strategy: str,
    k: int,
    delay: float,
) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import LLMContextRecall, Faithfulness, ResponseRelevancy
    from ragas.llms import LangchainLLMWrapper
    from ragas.dataset_schema import SingleTurnSample
    from langchain_openai import ChatOpenAI

    logger.info("=== Strategy: %s  k=%d ===", strategy.upper(), k)

    samples = []
    for i, row in enumerate(testset):
        question = row.get("user_input", "")
        reference = row.get("reference", "")
        logger.info("  [%d/%d] %s", i + 1, len(testset), question[:60])
        try:
            answer, contexts = await run_rag_for_sample(question, strategy, k)
        except Exception as exc:
            logger.warning("  Sample %d failed for %s: %s", i + 1, strategy, exc)
            answer, contexts = "I don't know.", []
        samples.append({
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": reference,
        })
        if delay > 0:
            time.sleep(delay)

    eval_samples = [
        SingleTurnSample(
            user_input=s["user_input"],
            retrieved_contexts=s["retrieved_contexts"],
            response=s["response"],
            reference=s["reference"],
        )
        for s in samples
    ]
    dataset = EvaluationDataset(samples=eval_samples)
    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))

    run_config_kwargs = {}
    try:
        from ragas import RunConfig
        run_config_kwargs["run_config"] = RunConfig(timeout=360)
    except ImportError:
        pass

    result = evaluate(
        dataset=dataset,
        metrics=[LLMContextRecall(), Faithfulness(), ResponseRelevancy()],
        llm=evaluator_llm,
        **run_config_kwargs,
    )
    df = result.to_pandas()
    scores = {
        col: float(df[col].mean())
        for col in df.columns
        if df[col].dtype in ("float64", "float32")
    }
    scores["_strategy"] = strategy
    scores["_k"] = k
    logger.info(
        "  → recall=%.4f  faithfulness=%.4f  relevancy=%.4f",
        scores.get("context_recall", 0),
        scores.get("faithfulness", 0),
        scores.get("answer_relevancy", 0),
    )
    return scores


# ── Comparison table ──────────────────────────────────────────────────────────

def print_comparison_table(results: list[dict]) -> None:
    metrics = ["context_recall", "faithfulness", "answer_relevancy"]
    col_w = 20
    header = f"{'Strategy':<25}" + "".join(f"{m:>{col_w}}" for m in metrics) + f"{'Composite':>{col_w}}"
    sep = "-" * len(header)

    logger.info("\n" + sep)
    logger.info("MODULE 11 — ADVANCED RETRIEVAL STRATEGY COMPARISON")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)

    def composite(r: dict) -> float:
        return sum(r.get(m, 0.0) for m in metrics)

    sorted_results = sorted(results, key=composite, reverse=True)
    for r in sorted_results:
        comp = composite(r)
        row = f"{r['_strategy']:<25}" + "".join(
            f"{r.get(m, float('nan')):>{col_w}.4f}" for m in metrics
        ) + f"{comp:>{col_w}.4f}"
        logger.info(row)

    logger.info(sep)
    best = sorted_results[0]
    logger.info(
        "BEST strategy: %s  (composite=%.4f)",
        best["_strategy"], composite(best),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Module 11 advanced retrieval evaluation")
    parser.add_argument("--testset", default=str(TESTSET_PATH))
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Seconds between samples (higher = safer for Cohere rate limits)")
    parser.add_argument("--k", type=int, default=5, help="Top-k chunks to retrieve")
    parser.add_argument(
        "--skip", default="",
        help="Comma-separated strategy names to skip (e.g. --skip rerank,semantic)"
    )
    parser.add_argument(
        "--only", default="",
        help="Comma-separated strategy names to run exclusively (overrides --skip)"
    )
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = json.loads(Path(args.testset).read_text())
    logger.info("Loaded %d test samples", len(testset))

    # Determine which strategies to run
    if args.only:
        strategies_to_run = [s.strip() for s in args.only.split(",")]
    else:
        skip_set = {s.strip() for s in args.skip.split(",") if s.strip()}
        # Auto-skip rerank if no Cohere key
        if not os.environ.get("COHERE_API_KEY"):
            logger.warning("No COHERE_API_KEY — skipping 'rerank' strategy")
            skip_set.add("rerank")
        strategies_to_run = [s for s in ALL_STRATEGIES if s not in skip_set]

    logger.info("Running strategies: %s", strategies_to_run)

    # Load any previously saved partial results
    all_results: list[dict] = []
    if MODULE11_RESULTS_PATH.exists():
        existing = json.loads(MODULE11_RESULTS_PATH.read_text())
        done_strategies = {r["_strategy"] for r in existing if "_strategy" in r}
        remaining = [s for s in strategies_to_run if s not in done_strategies]
        if done_strategies:
            logger.info("Resuming — already done: %s", sorted(done_strategies))
            all_results = existing
            strategies_to_run = remaining

    for strategy in strategies_to_run:
        scores = asyncio.run(evaluate_strategy(testset, strategy, args.k, args.delay))
        all_results.append(scores)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        MODULE11_RESULTS_PATH.write_text(json.dumps(all_results, indent=2, default=str))
        logger.info("Saved partial results (%d/%d strategies complete)", len(all_results), len(strategies_to_run) + len(all_results) - len(strategies_to_run))

    print_comparison_table(all_results)
    logger.info("Full results saved to %s", MODULE11_RESULTS_PATH)


if __name__ == "__main__":
    main()
