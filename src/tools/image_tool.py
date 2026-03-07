"""Image generation tool — creates LinkedIn poster images using gpt-image-1."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path

from src.config import get_settings
from src.llm import get_async_openai

logger = logging.getLogger(__name__)

def _build_prompt(topic: str, analogy: str) -> str:
    return (
        f"A cinematic, award-winning digital art poster about: {topic[:120]}.\n\n"
        f"Central visual metaphor: {analogy[:180]}.\n\n"
        "Art direction:\n"
        "- Deep space / neon-noir atmosphere: dark background with electric purple, "
        "cobalt blue, and gold accent lighting\n"
        "- Surreal, hyper-detailed illustration style — like a Blade Runner concept art meets "
        "an Escher diagram\n"
        "- Show abstract data flows, glowing neural-network nodes, geometric fractals, "
        "or the metaphor object rendered in photorealistic detail against the dark backdrop\n"
        "- Dramatic volumetric lighting, cinematic depth of field, ultra-sharp focal point\n"
        "- Absolutely NO text, letters, words, or captions anywhere in the image\n"
        "- 1:1 square composition, professional magazine quality"
    )


async def generate_poster(topic: str, analogy: str) -> tuple[str, Path | None]:
    """Generate a high-quality poster image for a LinkedIn post.

    Returns (image_url_or_path, local_path). local_path is None on failure.
    """
    cfg = get_settings()
    prompt = _build_prompt(topic, analogy)

    try:
        client = get_async_openai()

        # gpt-image-1 only supports b64_json; dall-e-3 supports both
        use_b64 = cfg.image_model == "gpt-image-1"
        kwargs: dict = dict(
            model=cfg.image_model,
            prompt=prompt,
            size=cfg.image_size,
            n=1,
        )
        if use_b64:
            kwargs["response_format"] = "b64_json"
        else:
            kwargs["quality"] = cfg.image_quality   # "hd" for dall-e-3
            kwargs["style"] = "vivid"               # vivid > natural for dramatic posters
            kwargs["response_format"] = "url"

        response = await client.images.generate(**kwargs)
        item = response.data[0]

        if use_b64:
            b64 = item.b64_json or ""
            local_path = _save_b64_image(b64, topic)
            url = str(local_path) if local_path else ""
        else:
            url = item.url or ""
            local_path = await _download_image(url, topic)

        logger.info("Generated image for topic '%s'", topic[:50])
        return url, local_path

    except Exception:
        logger.error("Image generation failed for topic '%s'", topic[:50], exc_info=True)
        return "", None


def _save_b64_image(b64: str, topic: str) -> Path | None:
    """Decode base64 image bytes and save to disk."""
    if not b64:
        return None
    try:
        cfg = get_settings()
        safe_name = "".join(c if c.isalnum() else "_" for c in topic[:40])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = cfg.images_path / f"{timestamp}_{safe_name}.png"
        out_path.write_bytes(base64.b64decode(b64))
        logger.info("Saved image to %s", out_path)
        return out_path
    except Exception:
        logger.warning("Failed to save b64 image", exc_info=True)
        return None


async def _download_image(url: str, topic: str) -> Path | None:
    """Download the generated image to local disk and return its path."""
    if not url:
        return None
    try:
        import httpx
        cfg = get_settings()
        safe_name = "".join(c if c.isalnum() else "_" for c in topic[:40])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = cfg.images_path / f"{timestamp}_{safe_name}.png"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
        logger.info("Saved image to %s", out_path)
        return out_path
    except Exception:
        logger.warning("Failed to download image", exc_info=True)
        return None
