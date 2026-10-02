"""Aggregate items from all fetcher sources (blogs, GitHub, Hacker News)."""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from src.constants import (
    BLOG_FEEDS,
    DEDUP_SIMILARITY_THRESHOLD,
    DIGEST_MAX_AGE_HOURS,
    MAX_ITEMS_PER_SOURCE,
    OPENAI_CHANGELOG_SOURCE,
    THREAD_POOL_WORKERS,
)
from src.fetchers.blog_fetcher import fetch_blog_posts
from src.fetchers.github_fetcher import fetch_github_releases
from src.fetchers.hackernews_fetcher import fetch_hackernews_stories
from src.fetchers.huggingface_fetcher import fetch_huggingface_papers
from src.fetchers.openai_changelog_fetcher import fetch_openai_changelog
from src.logger import get_logger
from src.topic_config import get_active_topics

logger = get_logger(__name__)

# Blog candidates pulled before ranking — kept above DIGEST_MAX_RESULTS so a
# dozen lab feeds each get a real shot at the daily pick.
BLOG_MAX_RESULTS = 25


def _parse_published(value: str) -> datetime | None:
    """Parse a published timestamp from any source into aware UTC.

    The four fetchers emit slightly different shapes — trailing "Z", explicit
    offsets, and (historically) naive strings already stored in papers.json.
    A naive value is treated as UTC, which is what every source actually
    produces. Returns None when the value cannot be parsed at all.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _filter_by_recency(items: list[dict], max_age_hours: int) -> list[dict]:
    """Drop items published longer than max_age_hours ago.

    Blog feeds carry no cutoff of their own, so without this a quiet day can
    surface a week-old post as today's development. Items with an unparseable
    timestamp are kept: failing open costs a stale item, while failing closed
    could silently empty the digest.
    """
    if max_age_hours <= 0:
        return items

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    kept, stale, undated = [], 0, 0

    for item in items:
        published = _parse_published(item.get("published", ""))
        if published is None:
            undated += 1
            kept.append(item)
            continue
        if published < cutoff:
            stale += 1
            continue
        kept.append(item)

    if stale:
        logger.info("Dropped %d item(s) older than %dh", stale, max_age_hours)
    if undated:
        logger.warning("Kept %d item(s) with an unparseable published date", undated)

    return kept


def _cap_per_source(items: list[dict], max_per_source: int) -> list[dict]:
    """Limit how many slots any one source can occupy.

    Items must already be sorted newest-first: each source keeps its most
    recent entries. Without this a high-volume vendor blog crowds out the
    frontier labs — one held 4 of 10 slots on 28-Aug and won the daily pick.
    """
    if max_per_source <= 0:
        return items

    counts: dict[str, int] = {}
    kept, dropped = [], 0

    for item in items:
        source = item.get("source", "")
        seen = counts.get(source, 0)
        if seen >= max_per_source:
            dropped += 1
            continue
        counts[source] = seen + 1
        kept.append(item)

    if dropped:
        logger.info("Dropped %d item(s) over the %d-per-source cap", dropped, max_per_source)

    return kept


def _identity_of(item: dict) -> str:
    """The key that makes two fetched items the same item.

    Normally the URL. A source may override it when one URL covers many items:
    OpenAI's changelog is a single page holding every entry, with no permalinks,
    so keying on the URL there would collapse the whole source to one item.
    json_exporter._paper_identity honours the same field, so an item dedupes
    and is remembered as sent under one key rather than two.
    """
    return (item.get("identity") or item.get("url") or "").strip()


def _deduplicate_by_identity(items: list[dict]) -> list[dict]:
    """Remove items that resolve to the same identity, keeping the first."""
    seen: set[str] = set()
    unique = []
    for item in items:
        key = _identity_of(item)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(item)
    return unique


# Sources that report on other people's launches rather than making them.
# A lab's own post is preferred over coverage of it when the two collapse.
AGGREGATOR_SOURCES = {"Hacker News", "Hugging Face", "AI Alignment Forum"}

# The frontier labs' own blogs. Membership is what exempts an item from the
# topic-keyword gate below: these feeds are curated upstream, so being in them
# is the relevance signal.
# The changelog joins them: it is a lab's own release notes, which is as
# curated as a source gets, and keyword-gating it would drop a pricing change
# for naming no topic keyword.
CURATED_SOURCES = frozenset(BLOG_FEEDS) | {OPENAI_CHANGELOG_SOURCE}

# Version-like tokens: v1.2.0, 5.3, 3.5-turbo, GPT-4o. Two titles carrying
# different ones describe different releases however similar they read.
_VERSION_TOKEN = re.compile(r"\bv?\d+(?:[.\-]\d+)+\b|\bv\d+\b")


def _fuzzy_title(title: str) -> str:
    """Reduce a title to bare words for similarity comparison.

    Punctuation becomes whitespace, so "GPT-4o mini" and "GPT 4o mini" compare
    equal. That is right for fuzzy matching and wrong for identity, which is
    why json_exporter._identity_title normalizes far more conservatively —
    two similar titles are the same story, but two distinct keys must stay
    distinct.
    """
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", (title or "").lower()).split())


def _version_tokens(title: str) -> set[str]:
    """Extract version-like tokens from a title."""
    return set(_VERSION_TOKEN.findall((title or "").lower()))


def _is_same_story(a: dict, b: dict, threshold: float) -> bool:
    """Decide whether two items describe the same announcement.

    Only ever true across different sources. Every false positive observed in
    real data was same-source — "anthropic-sdk-python v1.3.0" and "v1.2.0"
    score 0.97 but are distinct releases, as do "GLM-5.3" and "GLM 5.2".
    Coverage of one launch, by contrast, shows up under different sources.
    Differing version tokens veto a match outright.
    """
    if a.get("source", "") == b.get("source", ""):
        return False

    title_a, title_b = _fuzzy_title(a.get("title", "")), _fuzzy_title(b.get("title", ""))
    if not title_a or not title_b:
        return False

    if _version_tokens(a.get("title", "")) != _version_tokens(b.get("title", "")):
        return False

    return SequenceMatcher(None, title_a, title_b).ratio() >= threshold


def _preferred_of(a: dict, b: dict) -> tuple[dict, dict]:
    """Return (keep, drop) — the lab's own post beats coverage of it."""
    a_is_coverage = a.get("source", "") in AGGREGATOR_SOURCES
    b_is_coverage = b.get("source", "") in AGGREGATOR_SOURCES
    if a_is_coverage and not b_is_coverage:
        return b, a
    return a, b


def _deduplicate_by_similarity(items: list[dict], threshold: float) -> list[dict]:
    """Collapse cross-source coverage of the same announcement.

    Runs after URL deduplication, which handles the exact-match case. This
    catches the same launch arriving as a lab blog post, a Hacker News thread
    and a Hugging Face paper under three different URLs, where all three would
    otherwise compete against each other for the daily pick.
    """
    if threshold <= 0:
        return items

    kept: list[dict] = []
    merged = 0

    for item in items:
        duplicate_index = None
        for index, existing in enumerate(kept):
            if _is_same_story(item, existing, threshold):
                duplicate_index = index
                break

        if duplicate_index is None:
            kept.append(item)
            continue

        keep, drop = _preferred_of(kept[duplicate_index], item)
        kept[duplicate_index] = keep
        merged += 1
        logger.info(
            "Merged duplicate: kept [%s] %r over [%s] %r",
            keep.get("source", ""),
            (keep.get("title", "") or "")[:60],
            drop.get("source", ""),
            (drop.get("title", "") or "")[:60],
        )

    if merged:
        logger.info("Merged %d cross-source duplicate(s)", merged)

    return kept


def fetch_all(max_results: int = 20, filter_keywords: list[str] | None = None) -> list[dict]:
    """Fetch items from all sources in parallel, deduplicate, and sort by date.

    Args:
        max_results: Maximum number of items to return
        filter_keywords: Keyword list used to filter every source to matching topics only

    Returns:
        Combined, deduplicated, keyword-filtered, and sorted list of items
    """
    fetchers = [
        ("Blogs", lambda: fetch_blog_posts(max_results=BLOG_MAX_RESULTS, max_age_hours=DIGEST_MAX_AGE_HOURS)),
        ("GitHub", fetch_github_releases),
        ("Hacker News", lambda: fetch_hackernews_stories(filter_keywords=filter_keywords)),
        ("HF Papers", lambda: fetch_huggingface_papers(filter_keywords=filter_keywords)),
        ("OpenAI Changelog", fetch_openai_changelog),
    ]

    all_items: list[dict] = []

    with ThreadPoolExecutor(max_workers=THREAD_POOL_WORKERS) as executor:
        future_to_source = {
            executor.submit(fn): name
            for name, fn in fetchers
        }

        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                results = future.result()
                logger.info("Fetched %d items from %s", len(results), source)
                all_items.extend(results)
            except Exception:
                logger.error("Failed to fetch from %s", source)

    # Drop anything too old to be "today's" development. Applied centrally so
    # every source gets the same treatment, not just the blogs that lack a
    # cutoff — this also backstops a per-source cutoff regressing.
    all_items = _filter_by_recency(all_items, DIGEST_MAX_AGE_HOURS)
    logger.info("After recency filter: %d items within %dh", len(all_items), DIGEST_MAX_AGE_HOURS)

    # Deduplicate on identity — the URL, unless a source supplies its own
    unique = _deduplicate_by_identity(all_items)
    logger.info("After identity deduplication: %d unique items", len(unique))

    # Then collapse cross-source coverage of the same launch
    unique = _deduplicate_by_similarity(unique, DEDUP_SIMILARITY_THRESHOLD)
    logger.info("After similarity deduplication: %d unique items", len(unique))

    # Keyword filter, then topic tagging.
    #
    # The keyword gate applies only to the open sources. Hacker News and
    # Hugging Face Daily Papers carry everything, so a topic test is the only
    # thing separating AI news from the rest. A frontier lab's own blog needs
    # no such test — and applying one there was actively harmful: it admitted
    # "StreetComplete on iOS is now in public beta" on the phrase "public beta"
    # while dropping DeepMind's "Introducing SynthID Bio" for naming no model.
    #
    # Tagging still runs on everything, so curated posts keep a topic_id for
    # the dashboard and for feedback weighting.
    if filter_keywords:
        topics = get_active_topics()
        kw_lower = [k.lower() for k in filter_keywords]
        filtered = []
        dropped = 0
        for item in unique:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if item.get("source", "") not in CURATED_SOURCES:
                if not any(kw in text for kw in kw_lower):
                    dropped += 1
                    continue
            # Tag with the first topic whose keywords match
            if not item.get("topic_id"):
                for topic in topics:
                    if any(kw.lower() in text for kw in topic["keywords"]):
                        item = {**item, "topic_id": topic["id"]}
                        break
            filtered.append(item)
        unique = filtered
        logger.info(
            "After keyword filter: %d items (%d off-topic items dropped from open sources)",
            len(unique), dropped,
        )

    # Sort by published date (most recent first)
    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Cap per source after sorting so each source keeps its freshest items
    unique = _cap_per_source(unique, MAX_ITEMS_PER_SOURCE)
    logger.info("After per-source cap: %d items", len(unique))

    return unique[:max_results]
