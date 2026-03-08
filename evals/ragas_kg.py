"""Task 6+ — RAGAS evaluation with KG (Knowledge Graph) retrieval.

Runs the same testset through the Knowledge Graph retriever (KG traversal + Dense
multi-hop) and compares against baseline and HyDE results.

Usage:
    uv run python evals/ragas_kg.py
    uv run python evals/ragas_kg.py --testset evals/data/testset.json --delay 1.0
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
HYDE_PATH = Path("evals/results/hyde_results.json")
KG_RESULTS_PATH = Path("evals/results/kg_results.json")


def load_json(path: Path) -> dict | list:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


async def run_rag_for_sample(question: str, k: int = 5) -> tuple[str, list[str]]:
    """Run KG RAG for a single question. Returns (answer, retrieved_contexts)."""
    from src.retrieval.kg_retriever import KGRetriever
    from src.llm import get_async_openai
    from src.config import get_settings

    retriever = KGRetriever()
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


async def evaluate_kg(testset: list[dict], delay: float = 0.5, k: int = 5) -> dict:
    from ragas import EvaluationDataset, evaluate
    from ragas.metrics import LLMContextRecall, Faithfulness, ResponseRelevancy
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    samples = []
    for i, row in enumerate(testset):
        question = row.get("user_input", "")
        reference = row.get("reference", "")
        logger.info("[%d/%d] KG: %s", i + 1, len(testset), question[:60])
        answer, contexts = await run_rag_for_sample(question, k=k)
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
    df = result.to_pandas()
    return {col: float(df[col].mean()) for col in df.columns if df[col].dtype in ("float64", "float32")}


def print_three_way_comparison(baseline: dict, hyde: dict, kg: dict) -> None:
    metrics = sorted(set(baseline) | set(hyde) | set(kg))
    col_w = 18

    header = (
        f"{'Metric':<35} {'Baseline (Dense)':>{col_w}} "
        f"{'HyDE':>{col_w}} {'KG+Dense':>{col_w}} "
        f"{'Delta vs Base':>{col_w}}"
    )
    sep = "-" * len(header)
    logger.info("\n" + sep)
    logger.info("RETRIEVAL COMPARISON: Dense vs HyDE vs KG+Dense")
    logger.info(sep)
    logger.info(header)
    logger.info(sep)
    for m in metrics:
        b = baseline.get(m)
        h = hyde.get(m)
        k = kg.get(m)
        if isinstance(b, (int, float)) and isinstance(h, (int, float)) and isinstance(k, (int, float)):
            delta = k - b
            sign = "+" if delta >= 0 else ""
            logger.info(
                f"{m:<35} {b:>{col_w}.4f} {h:>{col_w}.4f} {k:>{col_w}.4f} {sign}{delta:>{col_w-1}.4f}"
            )
    logger.info(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS KG retrieval evaluation + comparison")
    parser.add_argument("--testset", default=str(TESTSET_PATH))
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--k", type=int, default=5, help="Top-k chunks to retrieve")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = load_json(Path(args.testset))
    logger.info("Loaded %d test samples", len(testset))

    kg_results = asyncio.run(evaluate_kg(testset, delay=args.delay, k=args.k))

    KG_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KG_RESULTS_PATH.write_text(json.dumps(kg_results, indent=2, default=str))
    logger.info("Saved KG results to %s", KG_RESULTS_PATH)

    if BASELINE_PATH.exists() and HYDE_PATH.exists():
        baseline = load_json(BASELINE_PATH)
        hyde = load_json(HYDE_PATH)
        print_three_way_comparison(baseline, hyde, kg_results)
    else:
        logger.info("KG results: %s", kg_results)


if __name__ == "__main__":
    main()
