"""Fetch developer product updates from major AI lab blogs."""

from datetime import datetime
import socket

import feedparser

from src.constants import BLOG_FEEDS, REQUEST_TIMEOUT
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


@retry_with_backoff(
    max_retries=2,
    base_delay=1.0,
    exceptions=(socket.timeout, OSError),
)
def _parse_blog_feed(url: str):
    """Parse blog RSS feed with retry on timeout."""
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(REQUEST_TIMEOUT)
    try:
        return feedparser.parse(url)
    finally:
        socket.setdefaulttimeout(old_timeout)


def _parse_date(entry: dict) -> str:
    """Parse publication date from feed entry."""
    # Try common date fields
    for field in ["published", "updated", "created"]:
        date_str = entry.get(field, "")
        if date_str:
            try:
                # feedparser provides parsed time tuples
                parsed = entry.get(f"{field}_parsed")
                if parsed:
                    return datetime(*parsed[:6]).isoformat()
            except (TypeError, ValueError):
                pass
    return datetime.now().isoformat()


def _fetch_single_feed(source: str, url: str, max_per_source: int) -> list[dict]:
    """Fetch posts from a single RSS feed."""
    try:
        feed = _parse_blog_feed(url)

        if feed.bozo and not feed.entries:
            logger.warning("%s feed parse error", source)
            return []

        posts = []
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            # Clean summary (remove HTML tags if present)
            summary = summary.replace("<p>", "").replace("</p>", " ")
            summary = summary.replace("<br>", " ").replace("<br/>", " ")
            summary = " ".join(summary.split())  # Normalize whitespace
            if len(summary) > 500:
                summary = summary[:497] + "..."

            post = {
                "title": title.strip(),
                "description": summary.strip(),
                "source": source,
                "lab": source,
                "url": entry.get("link", ""),
                "published_at": _parse_date(entry),
                "type": "product_update",
                "authors": source,
                "topics": [],
            }
            posts.append(post)

            if len(posts) >= max_per_source:
                break

        return posts

    except socket.timeout:
        logger.error("%s blog request timed out", source)
        return []
    except Exception:
        logger.error("Failed to fetch %s blog", source)
        return []


def fetch_blog_posts(max_results: int = 5) -> list[dict]:
    """
    Fetch recent developer product updates from Tier 1 AI lab blogs.

    Args:
        max_results: Maximum total number of posts to return

    Returns:
        List of normalized post dictionaries
    """
    all_posts = []
    max_per_source = max(1, max_results // len(BLOG_FEEDS) + 1)

    for source, url in BLOG_FEEDS.items():
        posts = _fetch_single_feed(source, url, max_per_source)
        all_posts.extend(posts)

    # Sort by published date (most recent first)
    all_posts.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True,
    )

    return all_posts[:max_results]
