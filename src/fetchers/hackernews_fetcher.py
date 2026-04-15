"""Fetch top Hacker News stories filtered to AI/ML topics."""

import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone

from src.constants import HN_KEYWORDS, HN_MAX_STORIES, HN_MIN_SCORE, REQUEST_TIMEOUT
from src.logger import get_logger

logger = get_logger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def _fetch_json(url: str):
    """Fetch and parse JSON from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "AI-Dev-Digest"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _matches_keywords(title: str, keywords: list[str] | None = None) -> bool:
    """Check if title matches any keyword (case-insensitive)."""
    kw_list = keywords if keywords is not None else HN_KEYWORDS
    for kw in kw_list:
        if re.search(re.escape(kw), title, re.IGNORECASE):
            return True
    return False


def fetch_hackernews_stories(filter_keywords: list[str] | None = None) -> list[dict]:
    """Fetch top HN stories matching computer use agent keywords.

    Filters: score > HN_MIN_SCORE, published within last 24 hours.
    Returns top HN_MAX_STORIES matching stories.
    """
    try:
        story_ids = _fetch_json(f"{HN_API_BASE}/topstories.json")
    except Exception:
        logger.error("Could not fetch HN top stories")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    matches = []

    for story_id in story_ids[:100]:
        try:
            item = _fetch_json(f"{HN_API_BASE}/item/{story_id}.json")
        except Exception:
            continue

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
        url = item.get("url", "") or f"https://news.ycombinator.com/item?id={story_id}"

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
    logger.info("Found %d computer use agent stories on Hacker News", len(result))
    return result
