"""X (Twitter) API tool — fetches trending AI topics from recent tweets.

Requires X_BEARER_TOKEN in .env. If not set, returns an empty list gracefully
so the content pipeline continues with Tavily results only.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from src.config import get_settings
from src.tools.tavily_tool import TopicResult

logger = logging.getLogger(__name__)


async def search_x_topics(domain: str | None = None) -> list[TopicResult]:
    """Search X.com for trending AI/GenAI discussions."""
    cfg = get_settings()
    if not cfg.x_bearer_token:
        logger.info("X_BEARER_TOKEN not set — skipping X.com search")
        return []

    domain = domain or cfg.content_domain

    try:
        import tweepy

        client = tweepy.Client(bearer_token=cfg.x_bearer_token, wait_on_rate_limit=False)
        base_query = f'"{domain}" OR #AI OR #GenerativeAI OR #LLM -is:retweet lang:en'
        common_kwargs: dict = dict(
            max_results=min(cfg.x_max_results, 100),
            tweet_fields=["public_metrics", "created_at", "text", "attachments"],
            expansions=["attachments.media_keys"],
            media_fields=["url", "preview_image_url", "type", "alt_text"],
            sort_order="relevancy",
        )
        # Prefer tweets with media; fall back to all tweets if none found
        # tweepy.Client is synchronous — run in thread to avoid blocking event loop
        response = await asyncio.to_thread(
            client.search_recent_tweets, f"{base_query} has:media", **common_kwargs
        )
        if not response.data:
            response = await asyncio.to_thread(
                client.search_recent_tweets, base_query, **common_kwargs
            )

        # Build media key → URL lookup from includes
        media_lookup: dict[str, str] = {}
        if response.includes and "media" in response.includes:
            for media in response.includes["media"]:
                key = media.media_key
                # photos have .url; videos/gifs have .preview_image_url
                url = getattr(media, "url", None) or getattr(media, "preview_image_url", None) or ""
                if key and url:
                    media_lookup[key] = url

        results = []
        if response.data:
            for tweet in response.data:
                metrics = tweet.public_metrics or {}
                engagement = (
                    metrics.get("retweet_count", 0) * 2
                    + metrics.get("like_count", 0)
                    + metrics.get("reply_count", 0)
                )
                # Collect media URLs for this tweet
                media_urls: list[str] = []
                attachments = getattr(tweet, "attachments", None) or {}
                for mk in (attachments.get("media_keys") or []):
                    if mk in media_lookup:
                        media_urls.append(media_lookup[mk])

                results.append(
                    TopicResult(
                        title=tweet.text[:100],
                        description=tweet.text[:400],
                        url=f"https://x.com/i/web/status/{tweet.id}",
                        source="x.com",
                        score=min(engagement / 1000.0, 1.0),
                        media_urls=media_urls,
                    )
                )
        logger.info("X.com returned %d tweets for domain '%s'", len(results), domain)
        return results

    except ImportError:
        logger.warning("tweepy not installed — skipping X.com search")
        return []
    except Exception:
        logger.warning("X.com search failed — skipping", exc_info=True)
        return []
