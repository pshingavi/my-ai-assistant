"""Tavily web search tool — finds trending AI/GenAI topics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from tavily import TavilyClient

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TopicResult:
    title: str
    description: str
    url: str
    source: str = "tavily"
    score: float = 0.0
    media_urls: list[str] = field(default_factory=list)


async def search_trending_topics(domain: str | None = None) -> list[TopicResult]:
    """Search Tavily for the hottest trending topics in the given domain."""
    from datetime import datetime
    cfg = get_settings()
    domain = domain or cfg.content_domain
    client = TavilyClient(api_key=cfg.tavily_api_key)

    month_year = datetime.now().strftime("%B %Y")
    query = (
        f"most significant {domain} breakthrough research announcement {month_year} "
        f"site:arxiv.org OR site:openai.com OR site:deepmind.com OR site:huggingface.co "
        f"OR site:venturebeat.com OR site:techcrunch.com"
    )
    try:
        response = client.search(
            query=query,
            max_results=cfg.tavily_max_results,
            search_depth="advanced",
            include_answer=True,
            topic="news",
        )
        results = []
        for r in response.get("results", []):
            results.append(
                TopicResult(
                    title=r.get("title", ""),
                    description=r.get("content", "")[:400],
                    url=r.get("url", ""),
                    source="tavily",
                    score=r.get("score", 0.0),
                )
            )
        logger.info("Tavily returned %d results for domain '%s'", len(results), domain)
        return results
    except Exception:
        logger.error("Tavily search failed", exc_info=True)
        return []
