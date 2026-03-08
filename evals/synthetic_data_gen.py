"""Task 5 — Synthetic dataset generation using RAGAS TestsetGenerator.

Generates a golden Q&A dataset from the AIE9 course materials.
The same dataset is used for both baseline and HyDE evaluation.

Usage:
    uv run python evals/synthetic_data_gen.py
    uv run python evals/synthetic_data_gen.py --size 20 --output evals/data/testset.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = Path("evals/data/testset.json")
SAMPLE_DOCS_DIR = Path(__file__).parent.parent.parent / "Learn-AI-Engineering"


def load_sample_documents(max_files: int = 5):
    """Load a representative subset of course materials as LangChain Documents."""
    from langchain_community.document_loaders import TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    target_files = [
        SAMPLE_DOCS_DIR / "03_The_Agent_Loop" / "HealthWellnessGuide.txt",
        SAMPLE_DOCS_DIR / "04_Agentic_RAG_From_Scratch" / "fun_guide.md",
    ]

    # Also look for any .txt files in the data subdirs
    for mod in ["02_Dense_Vector_Retrieval", "03_The_Agent_Loop", "11_Advanced_Retrieval"]:
        for f in (SAMPLE_DOCS_DIR / mod / "data").glob("*.txt"):
            target_files.append(f)

    docs = []
    for f in target_files[:max_files]:
        if f.exists():
            try:
                loader = TextLoader(str(f), encoding="utf-8")
                docs.extend(loader.load())
                logger.info("Loaded: %s", f.name)
            except Exception:
                logger.warning("Could not load %s", f)

    if not docs:
        logger.warning("No documents found — using built-in sample text")
        from langchain_core.documents import Document
        docs = [Document(page_content=_SAMPLE_TEXT, metadata={"source": "sample"})]

    return docs


async def generate_testset(size: int = 15, output: Path = DEFAULT_OUTPUT) -> list[dict]:
    from dotenv import load_dotenv
    load_dotenv()

    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.testset import TestsetGenerator
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    logger.info("Generating synthetic testset (size=%d)...", size)
    docs = load_sample_documents()
    logger.info("Using %d documents for generation", len(docs))

    generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)
    dataset = generator.generate_with_langchain_docs(docs, testset_size=size)

    df = dataset.to_pandas()
    records = df.to_dict(orient="records")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, default=str))
    logger.info("✅ Saved %d samples to %s", len(records), output)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RAGAS synthetic testset")
    parser.add_argument("--size", type=int, default=15, help="Number of Q&A pairs (default: 15)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    args = parser.parse_args()
    asyncio.run(generate_testset(args.size, Path(args.output)))


_SAMPLE_TEXT = """
# AI Engineering Concepts

## Retrieval-Augmented Generation (RAG)
RAG is a technique that combines information retrieval with language model generation.
Instead of relying solely on the model's training data, RAG retrieves relevant documents
from a knowledge base and uses them as context for generation.

## Vector Embeddings
Embeddings are dense numerical representations of text. Similar texts have similar
embedding vectors. This allows semantic search: finding documents that are conceptually
related rather than just keyword-matched.

## Chunking Strategies
Documents must be split into chunks before embedding. Common strategies:
- Fixed-size chunking: split by character count
- Semantic chunking: split at natural topic boundaries
- Recursive character splitting: progressively smaller separators

## HyDE — Hypothetical Document Embeddings
HyDE improves retrieval by generating a hypothetical answer to a query,
then embedding that answer instead of the raw query. This bridges the
semantic gap between short queries and long technical documents.

## LangGraph and Multi-Agent Systems
LangGraph enables building stateful, multi-step AI agents as directed graphs.
Nodes perform computation; edges define control flow. Conditional edges
create agentic decision points where the graph branches based on runtime data.

## RAGAS Evaluation Framework
RAGAS measures RAG system quality across four key metrics:
- Faithfulness: are answers grounded in the retrieved context?
- Context Precision: is the retrieved context relevant?
- Context Recall: does retrieval capture all necessary information?
- Answer Relevancy: does the answer address the question asked?
"""


if __name__ == "__main__":
    main()
