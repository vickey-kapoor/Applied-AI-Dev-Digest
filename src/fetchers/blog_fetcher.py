"""Fetch development announcements from frontier AI lab blogs."""

from datetime import datetime, timedelta, timezone
import html
from html.parser import HTMLParser
import socket

import feedparser

from src.constants import (
    BLOG_FEEDS,
    BLOG_MAX_PER_SOURCE,
    DIGEST_MAX_AGE_HOURS,
    EXCLUDE_KEYWORDS,
    EXCLUDE_TITLE_PATTERNS,
    REQUEST_TIMEOUT,
)
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML content."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join("".join(self._parts).split())


def _is_tutorial(title: str) -> bool:
    """Check whether a title reads as a tutorial or how-to rather than news.

    Title-only by design: "how to" and friends appear legitimately inside the
    body of real release posts, so matching the summary would drop launches.
    """
    lowered = (title or "").lower()
    return any(pattern in lowered for pattern in EXCLUDE_TITLE_PATTERNS)


def _is_noise(post: dict) -> bool:
    """Whether a post from a curated lab feed is noise rather than news.

    Deliberately not a topic test. Everything in BLOG_FEEDS is a frontier lab's
    own blog, so a post there is a lab development by definition and does not
    have to prove it by containing a keyword. Requiring one dropped DeepMind's
    "Introducing SynthID Bio" and every one of Google Research's five most
    recent posts, while admitting anything that merely said "mistral" —
    including a funding round. Only genuine noise is excluded here: how-to
    posts and the explicit EXCLUDE_KEYWORDS blocklist.
    """
    if _is_tutorial(post.get("title", "")):
        return True
    text = f"{post.get('title', '')} {post.get('summary', '')}".lower()
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    extractor = _HTMLTextExtractor()
    extractor.feed(text)
    # Decode HTML entities (e.g. &amp; &#39; &quot;)
    return html.unescape(extractor.get_text())


@retry_with_backoff(exceptions=(socket.timeout, OSError))
def _parse_blog_feed(url: str):
    """Parse blog RSS feed with retry on timeout."""
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(REQUEST_TIMEOUT)
    try:
        return feedparser.parse(url)
    finally:
        socket.setdefaulttimeout(old_timeout)


def _parse_date(entry: dict) -> str:
    """Parse publication date from a feed entry as a timezone-aware UTC string.

    feedparser normalizes its *_parsed tuples to UTC, so attaching UTC here is
    correct rather than an assumption. Always returning an aware value keeps
    this consistent with the other fetchers — a mix of naive and aware
    timestamps makes downstream date comparisons raise TypeError.
    """
    # Try common date fields
    for field in ["published", "updated", "created"]:
        date_str = entry.get(field, "")
        if date_str:
            try:
                # feedparser provides parsed time tuples, already in UTC
                parsed = entry.get(f"{field}_parsed")
                if parsed:
                    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _fetch_single_feed(source: str, url: str, max_age_hours: int, max_per_source: int) -> list[dict]:
    """Fetch recent posts from a single lab feed.

    Selection is by publication date, not by position. Taking the first N
    entries meant 2,593 entries across the feeds became 55 considered, because
    N was 5 regardless of how much a lab had published; max_per_source is now
    only a safety bound against a pathological feed.
    """
    try:
        feed = _parse_blog_feed(url)

        if feed.bozo and not feed.entries:
            logger.warning("%s feed parse error — no entries returned", source)
            return []

        if not feed.entries:
            logger.warning("%s returned an empty feed", source)
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        posts = []
        for entry in feed.entries:
            published = _parse_date(entry)
            try:
                if datetime.fromisoformat(published) < cutoff:
                    continue
            except (TypeError, ValueError):
                pass  # unparseable date: keep it and let fetch_all decide

            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            # Clean summary (remove HTML tags)
            summary = _strip_html(summary)
            if len(summary) > 500:
                summary = summary[:497] + "..."

            post = {
                "title": title.strip(),
                "summary": summary.strip(),
                "url": entry.get("link", ""),
                "source": source,
                "published": published,
                "type": "announcement",
            }
            posts.append(post)

            if len(posts) >= max_per_source:
                break

        filtered = [p for p in posts if not _is_noise(p)]

        # Per-feed counts make an empty or dead feed visible in the Actions log
        # instead of it silently contributing nothing.
        logger.info(
            "%s: %d entries in feed, %d within %dh, %d kept after noise filter",
            source,
            len(feed.entries),
            len(posts),
            max_age_hours,
            len(filtered),
        )

        return filtered

    except socket.timeout:
        logger.error("%s blog request timed out", source)
        return []
    except Exception:
        logger.error("Failed to fetch %s blog", source)
        return []


def fetch_blog_posts(max_results: int = 5, max_age_hours: int = DIGEST_MAX_AGE_HOURS) -> list[dict]:
    """
    Fetch recent development announcements from frontier AI lab blogs.

    Takes no keyword list: these feeds are curated, so filtering them by topic
    keyword removed real launches and kept brand-name mentions. fetch_all still
    tags each post with a topic and filters the open sources.

    Args:
        max_results: Maximum total number of posts to return
        max_age_hours: Only return posts published within this window

    Returns:
        List of normalized post dictionaries
    """
    all_posts = []

    for source, url in BLOG_FEEDS.items():
        posts = _fetch_single_feed(source, url, max_age_hours, BLOG_MAX_PER_SOURCE)
        all_posts.extend(posts)

    # Sort by published date (most recent first)
    all_posts.sort(
        key=lambda x: x.get("published", ""),
        reverse=True,
    )

    return all_posts[:max_results]
