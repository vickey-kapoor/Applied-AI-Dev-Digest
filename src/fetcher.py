"""Aggregate items from every fetcher source, deduplicate them, and sort by date."""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from src.constants import (
    AGGREGATOR_MAX_ITEMS,
    ANTHROPIC_ENGINEERING_SOURCE,
    ANTHROPIC_RELEASE_NOTES_SOURCE,
    ANTHROPIC_SOURCE,
    BLOG_FEEDS,
    DEDUP_SIMILARITY_THRESHOLD,
    DIGEST_MAX_AGE_HOURS,
    DIGEST_MIN_CANDIDATES,
    EXCLUDE_KEYWORDS,
    MAX_ITEMS_PER_SOURCE,
    OPENAI_CHANGELOG_SOURCE,
    THREAD_POOL_WORKERS,
)
from src.fetchers.anthropic_fetcher import fetch_anthropic_posts
from src.fetchers.anthropic_release_notes_fetcher import fetch_anthropic_release_notes
from src.fetchers.blog_fetcher import fetch_blog_posts
from src.fetchers.github_fetcher import fetch_github_releases
from src.fetchers.hackernews_fetcher import fetch_hackernews_stories
from src.fetchers.huggingface_fetcher import fetch_huggingface_papers
from src.fetchers.openai_changelog_fetcher import fetch_openai_changelog
from src.logger import get_logger
from src.topic_config import best_topic_id, get_active_topics

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


def _cap_per_source(
    items: list[dict],
    max_per_source: int,
    min_candidates: int = 0,
    max_results: int | None = None,
) -> list[dict]:
    """Limit how many slots any one source can occupy.

    Items must already be sorted newest-first: each source keeps its most
    recent entries. Without this a high-volume vendor blog crowds out the
    frontier labs — one held 4 of 10 slots on 28-Aug and won the daily pick.

    An aggregator gets a tighter cap of its own. Hacker News won 23 of the 56
    top picks between 29-Aug and 27-Oct-2026, more than any lab source, on a
    digest whose subject is what the labs ship. Two HN slots a day is how it
    got there. One keeps the fastest route to a Qwen or DeepSeek release open
    while leaving the rest of the field to the labs themselves.

    `min_candidates` is a floor the cap will not cut below. The cap was sized
    against a pool of twenty, where dropping a source's third item costs
    nothing; on a thin day it is the pool. Measured 02-Nov-2026: 9 items in
    the recency window, 4 dropped here, 5 reaching the ranker, which rejected
    4 of those and sent a single item. Measured 03-Nov-2026 00:04 UTC: 13 in
    the window, 7 dropped, 6 left — and among the 7 was "Apriel Voice 27B
    Preview: An Open Model for Speech, Reasoning, and Tool Use", an
    open-weights voice model, which is the first thing on the ranking
    prompt's priority list. It was dropped for being the third Hugging Face
    item of the day while "Introducing the Grid Protectors Program", an
    electricity-grid programme, kept a slot.

    So below that floor the cap stands down. The ranker is the editorial filter
    and it has to see the pool; the cap exists to stop one source *dominating*
    a full pool, not to shrink a thin one.

    `max_results` is the caller's own bound, and standing the cap down has to
    respect what that bound then truncates. Returning the raw list would hand
    `fetch_all` more items than it keeps, and it keeps the newest — so one
    source with 20 fresh posts and another with a single older one gives a
    capped pool of 3, stands the cap down, and then truncation drops the
    second source entirely, which is the exact harm the cap was built for. The
    capped survivors are therefore reserved first, so every source keeps its
    allocation, and the overflow fills whatever room is left.
    """
    if max_per_source <= 0:
        return items

    counts: dict[str, int] = {}
    kept, overflow = [], []

    for item in items:
        source = item.get("source", "")
        limit = max_per_source
        if source in AGGREGATOR_SOURCES and 0 < AGGREGATOR_MAX_ITEMS < limit:
            limit = AGGREGATOR_MAX_ITEMS
        seen = counts.get(source, 0)
        if seen >= limit:
            overflow.append(item)
            continue
        counts[source] = seen + 1
        kept.append(item)

    dropped = len(overflow)
    if dropped:
        logger.info("Dropped %d item(s) over the %d-per-source cap", dropped, max_per_source)

    if overflow and len(kept) < min_candidates:
        # Restore up to max_results, not up to the floor. Filling to exactly
        # the floor sounds tidier and is worse: which overflow items that
        # keeps is decided by their position, and the sources that overflow
        # are the ones stamping date-only timestamps (Hugging Face Daily
        # Papers and the platform release notes both publish at T00:00:00),
        # so their order inside a day is arbitrary. Tried on 03-Nov-2026, a
        # floor of 10 restored two HF papers and left the open-weights voice
        # model behind — the same positional accident the floor exists to
        # undo. max_results is what the ranker is sized for, so the only cut
        # left is one the caller was going to make anyway.
        #
        # kept goes first and keeps its place: it holds each source's
        # allocation, so a source with one old item cannot be truncated out
        # by another source's twenty fresh ones.
        room = len(items) if max_results is None else max(max_results - len(kept), 0)
        restored = overflow[:room]
        logger.info(
            "Pool would fall to %d, below the floor of %d — standing the "
            "%d-per-source cap down and restoring %d of %d capped item(s)",
            len(kept),
            min_candidates,
            max_per_source,
            len(restored),
            dropped,
        )
        kept += restored
        # Restored items were taken out of a newest-first list, so appending
        # them leaves the pool out of date order. Re-sort: "most recent first"
        # is what the ranker's date-order fallback assumes.
        kept.sort(key=lambda x: x.get("published", ""), reverse=True)

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
# Anthropic joins them for the same reason: its two listings and its platform
# release notes are a lab's own writing, scraped only because the lab
# publishes no feed.
CURATED_SOURCES = frozenset(BLOG_FEEDS) | {
    OPENAI_CHANGELOG_SOURCE,
    ANTHROPIC_SOURCE,
    ANTHROPIC_ENGINEERING_SOURCE,
    ANTHROPIC_RELEASE_NOTES_SOURCE,
}

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
        ("Anthropic", fetch_anthropic_posts),
        ("Anthropic Release Notes", fetch_anthropic_release_notes),
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
    # Tagging still runs on everything, so a curated post keeps a topic_id:
    # the digest message shows it.
    if filter_keywords:
        topics = get_active_topics()
        kw_lower = [k.lower() for k in filter_keywords]
        filtered = []
        dropped = 0
        excluded = 0
        for item in unique:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if item.get("source", "") not in CURATED_SOURCES:
                if not any(kw in text for kw in kw_lower):
                    dropped += 1
                    continue
                # The corporate-news blocklist, which blog_fetcher has always
                # applied to the lab feeds, applied here too. The open sources
                # are the ones that actually carry this material: a lab's own
                # blog does not run the lawsuit, and Hacker News voted
                # "Anthropic trained Claude on illegally obtained Stanford
                # professors' books" onto the front page, where the keyword
                # "Claude" was enough to admit it.
                if any(kw in text for kw in EXCLUDE_KEYWORDS):
                    excluded += 1
                    continue
            # Tag with the topic the text fits best, not the first one listed
            if not item.get("topic_id"):
                topic_id = best_topic_id(text, topics, item.get("title", ""))
                if topic_id:
                    item = {**item, "topic_id": topic_id}
            filtered.append(item)
        unique = filtered
        logger.info(
            "After keyword filter: %d items (%d off-topic, %d excluded as "
            "corporate news, both from open sources)",
            len(unique), dropped, excluded,
        )

    # Sort by published date (most recent first)
    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Cap per source after sorting so each source keeps its freshest items
    unique = _cap_per_source(
        unique, MAX_ITEMS_PER_SOURCE, DIGEST_MIN_CANDIDATES, max_results
    )
    logger.info("After per-source cap: %d items", len(unique))

    return unique[:max_results]
