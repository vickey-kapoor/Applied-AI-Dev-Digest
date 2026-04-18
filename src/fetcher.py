"""Aggregate items from all fetcher sources (blogs, GitHub, Hacker News)."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.constants import THREAD_POOL_WORKERS
from src.fetchers.blog_fetcher import fetch_blog_posts
from src.fetchers.github_fetcher import fetch_github_releases
from src.fetchers.hackernews_fetcher import fetch_hackernews_stories
from src.fetchers.huggingface_fetcher import fetch_huggingface_papers
from src.logger import get_logger
from src.topic_config import get_active_topics

logger = get_logger(__name__)


def _deduplicate_by_url(items: list[dict]) -> list[dict]:
    """Remove duplicate items based on URL."""
    seen_urls: set[str] = set()
    unique = []
    for item in items:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique.append(item)
    return unique


def fetch_all(max_results: int = 20, filter_keywords: list[str] | None = None) -> list[dict]:
    """Fetch items from all sources in parallel, deduplicate, and sort by date.

    Args:
        max_results: Maximum number of items to return
        filter_keywords: Keyword list used to filter every source to matching topics only

    Returns:
        Combined, deduplicated, keyword-filtered, and sorted list of items
    """
    fetchers = [
        ("Blogs", lambda: fetch_blog_posts(max_results=10, filter_keywords=filter_keywords)),
        ("GitHub", fetch_github_releases),
        ("Hacker News", lambda: fetch_hackernews_stories(filter_keywords=filter_keywords)),
        ("HF Papers", lambda: fetch_huggingface_papers(filter_keywords=filter_keywords)),
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

    # Deduplicate by URL
    unique = _deduplicate_by_url(all_items)
    logger.info("After deduplication: %d unique items", len(unique))

    # Final keyword filter — drop anything that doesn't mention a topic keyword
    # Also assign topic_id to each item based on first matching topic
    if filter_keywords:
        topics = get_active_topics()
        kw_lower = [k.lower() for k in filter_keywords]
        filtered = []
        for item in unique:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if not any(kw in text for kw in kw_lower):
                continue
            # Tag with the first topic whose keywords match
            if not item.get("topic_id"):
                for topic in topics:
                    if any(kw.lower() in text for kw in topic["keywords"]):
                        item = {**item, "topic_id": topic["id"]}
                        break
            filtered.append(item)
        unique = filtered
        logger.info("After keyword filter: %d items match active topics", len(unique))

    # Sort by published date (most recent first)
    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    return unique[:max_results]
