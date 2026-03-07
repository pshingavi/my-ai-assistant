"""Task 6 — RAGAS evaluation with HyDE (advanced retrieval) + comparison table.

Runs the same testset through HyDE retrieval and compares against baseline.
Prints a side-by-side table and saves results.

Usage:
    uv run python evals/ragas_hyde.py
    uv run python evals/ragas_hyde.py --testset evals/data/testset.json --delay 1.0
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
BASELINE_PATH = Path("evals/results/baseline_results.json")
HYDE_RESULTS_PATH = Path("evals/results/hyde_results.json")


def load_json(path: Path) -> dict | list:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


async def run_rag_for_sample(question: str) -> tuple[str, list[str]]:
    """Run HyDE RAG for a single question. Returns (answer, retrieved_contexts)."""
    from src.retrieval.hyde_retriever import HyDERetriever
    from src.llm import get_async_openai
    from src.config import get_settings

    retriever = HyDERetriever()
    chunks = await retriever.retrieve(question, k=5)
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


async def evaluate_hyde(testset: list[dict], delay: float = 0.5) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import LLMContextRecall, Faithfulness, ResponseRelevancy
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    samples = []
    for i, row in enumerate(testset):
        question = row.get("user_input", "")
        reference = row.get("reference", "")
        logger.info("[%d/%d] HyDE: %s", i + 1, len(testset), question[:60])
        answer, contexts = await run_rag_for_sample(question)
        samples.append({
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": reference,
        })
        if delay > 0:
            time.sleep(delay)

    from ragas.dataset_schema import SingleTurnSample
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
    return dict(result)


def print_comparison(baseline: dict, hyde: dict) -> None:
    metrics = sorted(set(baseline) | set(hyde))
    col_w = 22

    header = f"{'Metric':<35} {'Baseline (Dense)':>{col_w}} {'HyDE':>{col_w}} {'Delta':>{col_w}}"
    sep = "-" * len(header)
    logger.info("\n" + sep)
    logger.info("RETRIEVAL COMPARISON: Dense vs HyDE")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)
    for m in metrics:
        b = baseline.get(m)
        h = hyde.get(m)
        if isinstance(b, (int, float)) and isinstance(h, (int, float)):
            delta = h - b
            sign = "+" if delta >= 0 else ""
            logger.info(
                f"{m:<35} {b:>{col_w}.4f} {h:>{col_w}.4f} {sign}{delta:>{col_w-1}.4f}"
            )
    logger.info(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS HyDE evaluation + comparison")
    parser.add_argument("--testset", default=str(TESTSET_PATH))
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = load_json(Path(args.testset))
    logger.info("Loaded %d test samples", len(testset))

    hyde_results = asyncio.run(evaluate_hyde(testset, delay=args.delay))

    HYDE_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    HYDE_RESULTS_PATH.write_text(json.dumps(hyde_results, indent=2, default=str))
    logger.info("Saved HyDE results to %s", HYDE_RESULTS_PATH)

    # Print comparison if baseline exists
    if BASELINE_PATH.exists():
        baseline = load_json(BASELINE_PATH)
        print_comparison(baseline, hyde_results)
    else:
        logger.info("Baseline not found — run ragas_baseline.py first for comparison")
        logger.info("HyDE results: %s", hyde_results)


if __name__ == "__main__":
    main()
