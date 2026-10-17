"""Fetch Anthropic's own posts from anthropic.com.

Anthropic has no feed. /rss.xml, /feed.xml, /index.xml, /news/rss.xml,
/news/feed.xml and /engineering/rss.xml all answer 404, which is why one
Anthropic item reached this digest in its whole history while Hacker News
supplied 179. The listing pages are the source instead: robots.txt says
`Allow: /`, both /news and /engineering answer 200 to a plain client, and so
do the post pages — the summarizer reads 7,000 to 12,000 characters from
them, where OpenAI's blog gives a 150-character meta description through
Cloudflare.

What is parsed is the content payload the listing page already carries, not
its markup. Each listing streams its posts as JSON objects holding `title`,
`summary`, `publishedOn` and `slug`, and those field names are the site's
content model rather than its presentation: the visible markup names classes
like `PublicationList-module-scss-module__KxYrHG__date`, whose hash changes
on every rebuild, and the visible list is also the short one — 10 posts
against the payload's 276, with a day-resolution date against the payload's
timestamp.

The scan is deliberately not anchored to how Next.js streams that payload.
Any JSON object in the document carrying both `publishedOn` and `slug` is
read as a post, so moving the payload between `self.__next_f`, an inline
`__NEXT_DATA__` or whatever comes next costs nothing. A shape change that
defeats it yields zero posts and a warning, never an exception: a redesign
should cost Anthropic coverage for a day, not the digest.
"""

import json
import re

import requests

from src.constants import (
    ANTHROPIC_LISTINGS,
    ANTHROPIC_MAX_ITEMS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

# The marker that says "a post object starts somewhere behind this".
_POST_FIELD = '"publishedOn"'

# A post object must carry a slug too; `publishedOn` alone also appears on
# the site's other content types.
_SLUG_FIELD = '"slug"'

# Each chunk of the streamed payload is a JSON string literal, so the document
# holds the content escaped once over. Decoding the literals turns \" back into
# " and ’ into the apostrophe, which is what the scan below reads.
_PUSHED_CHUNK = re.compile(r"\.push\(\[\d+\s*,\s*(\"(?:[^\"\\]|\\.)*\")", re.DOTALL)


@retry_with_backoff(exceptions=(requests.RequestException,))
def _get(url: str) -> str:
    """Fetch a listing page."""
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def _decoded_payloads(document: str) -> list[str]:
    """The document, plus every JSON string literal streamed inside it.

    The document itself comes first so a payload embedded unescaped — an
    inline `__NEXT_DATA__` script, say — is found without any unescaping at
    all. A literal that will not decode is skipped rather than raising.
    """
    texts = [document]
    for match in _PUSHED_CHUNK.finditer(document):
        try:
            texts.append(json.loads(match.group(1)))
        except (json.JSONDecodeError, ValueError):
            continue
    return texts


def _object_start(text: str, from_index: int) -> int | None:
    """Index of the `{` opening the object that contains from_index.

    Walks back counting braces, so a nested object's own `{` does not end the
    search. Quoted braces inside string values would mislead it; none of the
    content fields carry one, and a misread object simply fails to decode.
    """
    depth = 0
    index = from_index
    while index >= 0:
        char = text[index]
        if char == "}":
            depth += 1
        elif char == "{":
            if depth == 0:
                return index
            depth -= 1
        index -= 1
    return None


def _posts_in(text: str) -> list[dict]:
    """Every JSON object in text that reads as a post."""
    decoder = json.JSONDecoder()
    posts, seen_starts = [], set()

    for match in re.finditer(re.escape(_POST_FIELD), text):
        start = _object_start(text, match.start())
        if start is None or start in seen_starts:
            continue
        seen_starts.add(start)
        try:
            obj, _ = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("publishedOn") and obj.get("slug"):
            posts.append(obj)

    return posts


def _slug_of(post: dict) -> str:
    """The post's URL slug, from either shape the payload uses."""
    slug = post.get("slug")
    if isinstance(slug, dict):
        slug = slug.get("current")
    return (slug or "").strip().strip("/") if isinstance(slug, str) else ""


def _item_from(post: dict, source: str, prefix: str) -> dict | None:
    """Turn one payload post into a digest item, or None if it is unusable."""
    slug = _slug_of(post)
    title = (post.get("title") or "").strip()
    published = (post.get("publishedOn") or "").strip()
    if not slug or not title or not published:
        return None

    return {
        "title": title,
        # The listing's own summary, written by Anthropic. The summarizer reads
        # the full post anyway; this is what the ranker screens on.
        "summary": (post.get("summary") or "").strip(),
        "url": f"https://www.anthropic.com{prefix}{slug}",
        "source": source,
        # Dates arrive two ways: /news gives a timestamp with a trailing Z,
        # /engineering gives a bare date. fetcher._parse_published reads both,
        # treating the bare date as UTC midnight.
        "published": published,
        "type": "announcement",
    }


def _fetch_listing(url: str, source: str, prefix: str, max_items: int) -> list[dict]:
    """Fetch and parse one listing page."""
    document = _get(url)

    posts: list[dict] = []
    for text in _decoded_payloads(document):
        posts = _posts_in(text)
        if posts:
            break

    if not posts:
        logger.warning("No posts found in the %s listing — the page shape may have changed", source)
        return []

    items: dict[str, dict] = {}
    for post in posts:
        item = _item_from(post, source, prefix)
        # A post appears more than once in the payload; the first copy wins,
        # and keying on the URL keeps one item per post.
        if item and item["url"] not in items:
            items[item["url"]] = item

    newest = sorted(items.values(), key=lambda i: i["published"], reverse=True)
    logger.info("Parsed %d %s posts, keeping the newest %d", len(newest), source, max_items)
    return newest[:max_items]


def fetch_anthropic_posts(max_items: int = ANTHROPIC_MAX_ITEMS) -> list[dict]:
    """Fetch the newest posts from Anthropic's news and engineering listings.

    Args:
        max_items: Most items to keep per listing

    Returns:
        Items from both listings. A listing that cannot be read contributes
        nothing and leaves the other one's items in place — losing the
        engineering post should not cost the news post too.
    """
    items: list[dict] = []

    for url, (source, prefix) in ANTHROPIC_LISTINGS.items():
        try:
            items.extend(_fetch_listing(url, source, prefix, max_items))
        except Exception:
            logger.error("Failed to fetch the %s listing from %s", source, url)

    return items
