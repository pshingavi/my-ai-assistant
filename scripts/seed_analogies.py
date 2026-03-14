#!/usr/bin/env python3
"""
Creative Analogy Seeder — AI sub-agent that generates diverse, story-rich
analogy seeds for every concept in the knowledge graph.

Seeds are stored in data/analogy_seeds.json.
The byte pipeline reads these seeds and uses them as creative anchors,
guaranteeing every concept gets a unique, memorable, domain-diverse analogy
that a 10-year-old OR a 75-year-old can understand and enjoy.

Usage:
    uv run python scripts/seed_analogies.py
    uv run python scripts/seed_analogies.py --dry-run  # print without saving
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger("seed_analogies")

_PROJECT_ROOT = Path(__file__).parent.parent
_GRAPH_PATH   = _PROJECT_ROOT / "data" / "topic_graph.json"
_SEEDS_PATH   = _PROJECT_ROOT / "data" / "analogy_seeds.json"

# ── Creative Analogy Expert System Prompt ──────────────────────────────────────
_SEEDER_SYSTEM = """\
You are a world-class creative educator — part Pixar story artist, part Mr. Rogers, \
part David Attenborough. Your gift is turning complex technical ideas into short, \
vivid, emotionally resonant stories that ANYONE — a curious 10-year-old, a retired \
grandparent, a first-week engineering student — can immediately grasp and remember.

Your job: for each AI/ML concept below, invent ONE perfect analogy from everyday life. \
Requirements:
1. DIVERSE DOMAINS — use a completely different world for each concept. Never repeat \
   a domain (e.g., if one concept uses "post office", no other concept uses it). \
   Draw from: detective work, ocean voyages, bakeries, space missions, gardening, \
   hospitals, film production, treasure hunts, orchestras, sports stadiums, courtrooms, \
   railway stations, photo studios, zoos, construction sites, antique shops, weather \
   forecasting, circuses, archaeology, journalism, theater, aquariums, clock repair, \
   carpentry, astronomy observatories, safari parks, etc.

2. STORY-FIRST — write a MICRO-STORY (3-5 sentences) with characters, conflict, \
   and resolution. The analogy must feel like the opening of a short film, not a \
   textbook sentence. Include: WHO the characters are, WHAT they do, and WHY it matters.

3. ACCESSIBLY SIMPLE — No jargon. If you need a technical word in the analogy, \
   immediately explain it as a child would understand.

4. EMOTIONALLY VIVID — Choose settings and characters the reader can SEE and FEEL. \
   A dusty old clock-repair shop. A neon-lit aquarium at midnight. A soccer stadium \
   in a downpour.

5. MECHANICALLY ACCURATE — The analogy must correctly mirror how the concept actually \
   works, not just vaguely resemble it.

6. VISUAL SCENE — also output a scene description for animation:
   - character1: who gives/processes (emoji + role label ≤12 chars + description)
   - character2: who receives/transforms (emoji + role label ≤12 chars + description)
   - item1: what is exchanged/processed (emoji + label ≤10 chars)
   - item2: secondary item exchanged (emoji + label ≤10 chars)
   - setting: the physical place (≤15 words, rich and specific)
   - accentColor: hex color matching the mood

7. IMAGE PROMPT — a CINEMATIC FILM STILL description (≤120 words, 16:9, no text in image, \
   characters mid-action, specific lighting, camera angle, mood).

Output STRICT JSON array:
[
  {
    "concept": "<exact concept name>",
    "topic": "<topic name>",
    "domain": "<one-word domain label, e.g. post_office, detective, astronomy>",
    "analogy": "<micro-story 3-5 sentences>",
    "scene_setting": "<rich physical setting, ≤15 words>",
    "character1": {"emoji": "<e>", "label": "<≤12 chars>", "description": "<what they represent>"},
    "character2": {"emoji": "<e>", "label": "<≤12 chars>", "description": "<what they represent>"},
    "item1": {"emoji": "<e>", "label": "<≤10 chars>"},
    "item2": {"emoji": "<e>", "label": "<≤10 chars>"},
    "accentColor": "<hex>",
    "image_prompt": "<cinematic film still, ≤120 words>"
  }
]

CRITICAL: every concept must have a DIFFERENT domain. List used domains and avoid repeating.
Write as if each analogy is the opening monologue of a Pixar short film.
"""


def load_all_concepts() -> list[dict]:
    """Load all topics and their concepts from the knowledge graph."""
    with open(_GRAPH_PATH) as f:
        graph = json.load(f)

    concepts = []
    seen = set()
    for node in graph.get("nodes", []):
        topic_name = node.get("name", "")
        is_post = node.get("is_post", False)
        if is_post:
            continue  # skip generated posts, focus on course topics
        for concept in node.get("concepts", []):
            key = (topic_name, concept)
            if key not in seen:
                seen.add(key)
                concepts.append({"topic": topic_name, "concept": concept})

    logger.info("Loaded %d concepts across %d unique topics", len(concepts),
                len({c["topic"] for c in concepts}))
    return concepts


async def generate_seeds_batch(
    concepts: list[dict], client, cfg, used_domains: set[str]
) -> list[dict]:
    """Call the creative analogy expert LLM to seed a batch of concepts."""
    concept_list = "\n".join(
        f"{i+1}. Topic: {c['topic']} | Concept: {c['concept']}"
        for i, c in enumerate(concepts)
    )
    avoid = ", ".join(sorted(used_domains)) if used_domains else "none yet"

    user_msg = f"""Generate creative analogy seeds for these {len(concepts)} AI/ML concepts.

DOMAINS ALREADY USED (avoid these entirely): {avoid}

Each concept MUST use a different domain from each other AND from the used list above.

CONCEPTS:
{concept_list}

Output a JSON object: {{ "seeds": [ ...array of {len(concepts)} seeds... ] }}
One seed per concept, in order. Make each analogy a vivid micro-story (3-5 sentences) \
that a curious 10-year-old would love to watch as a Pixar short film.
"""

    resp = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=[
            {"role": "system", "content": _SEEDER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=4000,
        temperature=0.92,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            seeds = data.get("seeds") or data.get("concepts") or list(data.values())[0]
        else:
            seeds = data
        if not isinstance(seeds, list):
            raise ValueError("Expected a list")
        return seeds
    except Exception as e:
        logger.error("Failed to parse batch response: %s | raw: %s", e, raw[:300])
        return []


async def generate_all_seeds(concepts: list[dict], client, cfg, batch_size: int = 10) -> list[dict]:
    """Process concepts in batches to stay within token limits."""
    all_seeds = []
    used_domains: set[str] = set()

    for i in range(0, len(concepts), batch_size):
        batch = concepts[i:i + batch_size]
        logger.info(
            "Batch %d/%d — seeding concepts %d–%d (used %d domains so far)",
            i // batch_size + 1,
            (len(concepts) + batch_size - 1) // batch_size,
            i + 1,
            min(i + batch_size, len(concepts)),
            len(used_domains),
        )
        seeds = await generate_seeds_batch(batch, client, cfg, used_domains)
        # Track domains used so next batch avoids them
        for s in seeds:
            if d := s.get("domain"):
                used_domains.add(d.lower().replace(" ", "_"))
        all_seeds.extend(seeds)
        logger.info("  → Got %d seeds (total so far: %d)", len(seeds), len(all_seeds))

    return all_seeds


def merge_seeds(existing: dict, new_seeds: list[dict]) -> dict:
    """Merge new seeds into existing, keyed by concept name."""
    updated = dict(existing)
    for seed in new_seeds:
        concept = seed.get("concept", "").strip()
        if concept:
            updated[concept] = seed
    return updated


async def main(dry_run: bool = False) -> None:
    import sys
    sys.path.insert(0, str(_PROJECT_ROOT))

    from src.config import get_settings
    from src.llm import get_async_openai

    cfg = get_settings()
    client = get_async_openai()

    concepts = load_all_concepts()
    if not concepts:
        logger.error("No concepts found in topic graph!")
        return

    # Load existing seeds
    existing_seeds: dict = {}
    if _SEEDS_PATH.exists():
        try:
            with open(_SEEDS_PATH) as f:
                existing_seeds = json.load(f)
            logger.info("Loaded %d existing seeds", len(existing_seeds))
        except Exception:
            pass

    seeds = await generate_all_seeds(concepts, client, cfg, batch_size=8)

    if not seeds:
        logger.error("No seeds generated — check LLM response above")
        return

    # Report domain diversity
    domains = [s.get("domain", "unknown") for s in seeds]
    unique_domains = set(domains)
    logger.info("Domain diversity: %d unique domains across %d concepts", len(unique_domains), len(seeds))
    duplicates = [d for d in domains if domains.count(d) > 1]
    if duplicates:
        logger.warning("Duplicate domains found: %s", set(duplicates))

    if dry_run:
        logger.info("DRY RUN — printing seeds, not saving")
        for s in seeds[:5]:
            print(f"\n{'='*60}")
            print(f"Concept: {s.get('concept')}")
            print(f"Domain:  {s.get('domain')}")
            print(f"Analogy: {s.get('analogy','')[:200]}")
            print(f"Setting: {s.get('scene_setting')}")
        return

    merged = merge_seeds(existing_seeds, seeds)
    _SEEDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SEEDS_PATH, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d seeds to %s", len(merged), _SEEDS_PATH)

    # Print a sample for verification
    print("\n" + "="*60)
    print("SAMPLE SEEDS (first 5):")
    for s in seeds[:5]:
        print(f"\n  [{s.get('domain','?').upper()}] {s.get('concept')}")
        print(f"  {s.get('analogy','')[:180]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate creative analogy seeds for all concepts")
    parser.add_argument("--dry-run", action="store_true", help="Print seeds without saving")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
