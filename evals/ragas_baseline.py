"""Task 5 — RAGAS baseline evaluation using Dense Vector Retrieval.

Loads the synthetic testset, runs each question through the dense retriever
and a simple RAG chain, then evaluates with RAGAS metrics.

Usage:
    uv run python evals/ragas_baseline.py
    uv run python evals/ragas_baseline.py --testset evals/data/testset.json --delay 1.0
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
RESULTS_PATH = Path("evals/results/baseline_results.json")


def load_testset(path: Path) -> list[dict]:
    if not path.exists():
        logger.error("Testset not found: %s — run synthetic_data_gen.py first", path)
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


async def run_rag_for_sample(question: str) -> tuple[str, list[str]]:
    """Run dense RAG for a single question. Returns (answer, retrieved_contexts)."""
    from src.retrieval.dense_retriever import DenseRetriever
    from src.llm import get_async_openai
    from src.config import get_settings

    retriever = DenseRetriever()
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


async def evaluate_baseline(testset: list[dict], delay: float = 0.5) -> dict:
    """Run all samples through dense RAG and evaluate with RAGAS."""
    from ragas import EvaluationDataset
    from ragas import evaluate
    from ragas.metrics import LLMContextRecall, Faithfulness, ResponseRelevancy
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    # Run RAG for each sample
    samples = []
    for i, row in enumerate(testset):
        question = row.get("user_input", "")
        reference = row.get("reference", "")
        logger.info("[%d/%d] Running: %s", i + 1, len(testset), question[:60])

        answer, contexts = await run_rag_for_sample(question)
        samples.append({
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": answer,
            "reference": reference,
        })
        if delay > 0:
            time.sleep(delay)

    # Build EvaluationDataset
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

    # Evaluate
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


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS baseline evaluation (dense retrieval)")
    parser.add_argument("--testset", default=str(TESTSET_PATH))
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between samples")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = load_testset(Path(args.testset))
    logger.info("Loaded %d test samples", len(testset))

    results = asyncio.run(evaluate_baseline(testset, delay=args.delay))

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))

    logger.info("\n" + "=" * 50)
    logger.info("BASELINE (Dense Retrieval) Results:")
    logger.info("=" * 50)
    for metric, score in results.items():
        logger.info("  %-35s %.4f", metric, score)
    logger.info("=" * 50)
    logger.info("Saved to %s", RESULTS_PATH)


if __name__ == "__main__":
    main()
