"""Image generation — uses gpt-image-1 (OpenAI's latest) for photorealistic analogy scenes."""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path

from src.config import get_settings
from src.llm import get_async_openai

logger = logging.getLogger(__name__)


def _build_prompt(topic: str, analogy: str) -> str:
    """Build a rich, photorealistic scene prompt that visualises the analogy."""
    return (
        f"A photorealistic, cinematic scene illustrating this AI concept through analogy:\n\n"
        f"Concept: {topic[:100]}\n"
        f"Analogy: {analogy[:200]}\n\n"
        "Visual requirements:\n"
        "- Render the ANALOGY as a real, tangible physical scene — show the actual characters "
        "and objects from the analogy (e.g. if the analogy mentions a chef, show a real chef in a kitchen)\n"
        "- Photorealistic quality: dramatic cinematic lighting, shallow depth of field, professional photography style\n"
        "- Rich colour grading: warm golden-hour tones or cool blue tech atmosphere depending on context\n"
        "- The scene should feel ALIVE — action in progress, not a still pose\n"
        "- Characters/objects should be mid-action (chef actively reaching for ingredients, librarian scanning shelves, etc.)\n"
        "- Include subtle visual metaphors that connect the analogy to the AI concept\n"
        "- Absolutely NO text, words, labels, or captions in the image\n"
        "- 16:9 cinematic widescreen composition, magazine cover quality\n"
        "- Ultra-sharp focal point on the primary character/action, background beautifully blurred"
    )


async def generate_poster(topic: str, analogy: str, image_prompt: str | None = None) -> tuple[str, Path | None]:
    """Generate a high-quality analogy scene image.

    Returns (image_url_or_path, local_path). local_path is None on failure.
    """
    cfg = get_settings()
    prompt = image_prompt if image_prompt else _build_prompt(topic, analogy)

    try:
        client = get_async_openai()

        kwargs: dict = dict(
            model=cfg.image_model,
            prompt=prompt,
            size=cfg.image_size,
            n=1,
            quality=cfg.image_quality,
        )

        response = await client.images.generate(**kwargs)
        item = response.data[0]

        # gpt-image-1 returns b64_json by default
        if item.b64_json:
            local_path = _save_b64_image(item.b64_json, topic)
            url = str(local_path) if local_path else ""
        elif item.url:
            url = item.url
            local_path = await _download_image(url, topic)
        else:
            return "", None

        logger.info("Generated image for topic '%s' using %s", topic[:50], cfg.image_model)
        return url, local_path

    except Exception:
        logger.error("Image generation failed for topic '%s'", topic[:50], exc_info=True)
        return "", None


def _save_b64_image(b64: str, topic: str) -> Path | None:
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
    if not url:
        return None
    try:
        import httpx
        cfg = get_settings()
        safe_name = "".join(c if c.isalnum() else "_" for c in topic[:40])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = cfg.images_path / f"{timestamp}_{safe_name}.png"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
        logger.info("Saved image to %s", out_path)
        return out_path
    except Exception:
        logger.warning("Failed to download image", exc_info=True)
        return None
