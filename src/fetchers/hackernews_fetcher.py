"""Fetch top Hacker News stories filtered to AI lab developments."""

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from src.constants import (
    HN_MAX_STORIES,
    HN_MIN_SCORE,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.logger import get_logger

logger = get_logger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# Stories to inspect from the top list, and how many to fetch at once.
# Each story is a separate HTTP request, so fetching them one at a time made
# this the slowest step in the pipeline by a wide margin (~13s of a ~20s run).
HN_STORIES_TO_SCAN = 100
HN_FETCH_WORKERS = 10


def _fetch_json(url: str):
    """Fetch and parse JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _fetch_story(story_id: int) -> dict | None:
    """Fetch a single story, returning None rather than raising.

    A failure here should cost one story, not the whole batch.
    """
    try:
        return _fetch_json(f"{HN_API_BASE}/item/{story_id}.json")
    except Exception:
        return None


def _matches_keywords(title: str, keywords: list[str] | None = None) -> bool:
    """Check if title matches any keyword (case-insensitive).

    No keywords means nothing matches. There used to be a built-in default
    list here, which fetch_all never used and which had quietly diverged from
    the topic config it shadowed. An empty list now reads as what it is: every
    topic is switched off, so no Hacker News story is on topic.
    """
    for kw in keywords or ():
        if re.search(re.escape(kw), title, re.IGNORECASE):
            return True
    return False


def fetch_hackernews_stories(filter_keywords: list[str] | None = None) -> list[dict]:
    """Fetch top HN stories matching AI lab development keywords.

    Filters: score > HN_MIN_SCORE, published within last 24 hours, and a
    keyword match on the title — fetch_all supplies the live topic keywords.
    Returns top HN_MAX_STORIES matching stories.
    """
    if not filter_keywords:
        logger.info("No active topic keywords — skipping Hacker News")
        return []

    try:
        story_ids = _fetch_json(f"{HN_API_BASE}/topstories.json")
    except Exception:
        logger.error("Could not fetch HN top stories")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    matches = []

    # Fetched concurrently: these are independent single-item reads against a
    # public read-only API, and doing them in sequence dominated the runtime.
    with ThreadPoolExecutor(max_workers=HN_FETCH_WORKERS) as executor:
        items = list(executor.map(_fetch_story, story_ids[:HN_STORIES_TO_SCAN]))

    for item in items:
        if not item or item.get("type") != "story":
            continue

        title = item.get("title", "")
        score = item.get("score", 0)
        timestamp = item.get("time", 0)

        # Check score threshold
        if score < HN_MIN_SCORE:
            continue

        # Check recency
        try:
            published_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OSError, ValueError):
            continue

        if published_dt < cutoff:
            continue

        # Check keyword match
        if not _matches_keywords(title, filter_keywords):
            continue

        comments = item.get("descendants", 0)
        # The id comes from the item now that stories are fetched in parallel
        # rather than iterated by id.
        url = item.get("url", "") or f"https://news.ycombinator.com/item?id={item.get('id', '')}"

        matches.append({
            "title": title,
            "summary": f"{score} points \u00b7 {comments} comments",
            "url": url,
            "source": "Hacker News",
            "score": score,
            "published": published_dt.isoformat(),
            "type": "discussion",
        })

    # Sort by score descending, take top N
    matches.sort(key=lambda x: x.get("score", 0), reverse=True)
    result = matches[:HN_MAX_STORIES]
    logger.info("Found %d AI lab development stories on Hacker News", len(result))
    return result
