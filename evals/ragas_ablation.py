"""Retrieval ablation study — evaluates combinations of retriever × top-k.

Tests 6 combinations to identify the best hyperparameter configuration:
  retrievers : dense, hyde, kg
  k values   : 3, 5, 8

All combinations use the same synthetic testset and RAGAS metrics.
Results saved to evals/results/ablation_results.json.

Usage:
    uv run python evals/ragas_ablation.py
    uv run python evals/ragas_ablation.py --delay 1.0 --k-values 3,5 --retrievers dense,hyde
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

TESTSET_PATH = Path("evals/data/testset.json")
ABLATION_RESULTS_PATH = Path("evals/results/ablation_results.json")

# ── Retriever factory ─────────────────────────────────────────────────────────

async def get_retriever(name: str):
    if name == "dense":
        from src.retrieval.dense_retriever import DenseRetriever
        return DenseRetriever()
    elif name == "hyde":
        from src.retrieval.hyde_retriever import HyDERetriever
        return HyDERetriever()
    elif name == "kg":
        from src.retrieval.kg_retriever import KGRetriever
        return KGRetriever()
    else:
        raise ValueError(f"Unknown retriever: {name}")


async def run_rag_for_sample(question: str, retriever_name: str, k: int) -> tuple[str, list[str]]:
    from src.llm import get_async_openai
    from src.config import get_settings

    retriever = await get_retriever(retriever_name)
    chunks = await retriever.retrieve(question, k=k)
    context_str = "\n\n".join(c.content for c in chunks)
    retrieved_contexts = [c.content for c in chunks]

    cfg = get_settings()
    client = get_async_openai()
    prompt = (
        "Answer the question based only on the context below. "
        "If the context doesn't contain the answer, say 'I don't know'.\n\n"
        f"Context:\n{context_str}\n\nQuestion: {question}"
    )
    response = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0,
    )
    answer = response.choices[0].message.content or ""
    return answer, retrieved_contexts


async def evaluate_combo(
    testset: list[dict],
    retriever_name: str,
    k: int,
    delay: float = 0.5,
) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import LLMContextRecall, Faithfulness, ResponseRelevancy
    from ragas.llms import LangchainLLMWrapper
    from ragas.dataset_schema import SingleTurnSample
    from langchain_openai import ChatOpenAI

    logger.info("=== Evaluating: retriever=%s  k=%d ===", retriever_name, k)

    samples = []
    for i, row in enumerate(testset):
        question = row.get("user_input", "")
        reference = row.get("reference", "")
        logger.info("  [%d/%d] %s", i + 1, len(testset), question[:55])
        answer, contexts = await run_rag_for_sample(question, retriever_name, k)
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
    scores = {col: float(df[col].mean()) for col in df.columns if df[col].dtype in ("float64", "float32")}
    scores["_retriever"] = retriever_name
    scores["_k"] = k
    return scores


def print_ablation_table(results: list[dict]) -> None:
    metrics = ["context_recall", "faithfulness", "answer_relevancy"]
    col_w = 20
    header = f"{'Config':<25}" + "".join(f"{m:>{col_w}}" for m in metrics)
    sep = "-" * len(header)
    logger.info("\n" + sep)
    logger.info("ABLATION RESULTS: Retriever × Top-K")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)
    for r in results:
        label = f"{r['_retriever']}  k={r['_k']}"
        row = f"{label:<25}" + "".join(
            f"{r.get(m, float('nan')):>{col_w}.4f}" for m in metrics
        )
        logger.info(row)
    logger.info(sep)

    # Best overall
    def composite(r: dict) -> float:
        return sum(r.get(m, 0.0) for m in metrics)

    best = max(results, key=composite)
    logger.info(
        "Best combo: retriever=%s  k=%d  (composite=%.4f)",
        best["_retriever"], best["_k"], composite(best),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval ablation study")
    parser.add_argument("--testset", default=str(TESTSET_PATH))
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between samples")
    parser.add_argument(
        "--k-values", default="3,5,8",
        help="Comma-separated top-k values to test (default: 3,5,8)"
    )
    parser.add_argument(
        "--retrievers", default="dense,hyde,kg",
        help="Comma-separated retriever names (default: dense,hyde,kg)"
    )
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = json.loads(Path(args.testset).read_text())
    logger.info("Loaded %d test samples", len(testset))

    k_values = [int(x) for x in args.k_values.split(",")]
    retriever_names = [x.strip() for x in args.retrievers.split(",")]

    all_results: list[dict] = []
    for retriever_name in retriever_names:
        for k in k_values:
            scores = asyncio.run(evaluate_combo(testset, retriever_name, k, delay=args.delay))
            all_results.append(scores)
            # Save incrementally
            ABLATION_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            ABLATION_RESULTS_PATH.write_text(json.dumps(all_results, indent=2, default=str))
            logger.info("Saved partial ablation results (%d/%d)", len(all_results), len(retriever_names) * len(k_values))

    print_ablation_table(all_results)
    logger.info("Full ablation results saved to %s", ABLATION_RESULTS_PATH)


if __name__ == "__main__":
    main()
