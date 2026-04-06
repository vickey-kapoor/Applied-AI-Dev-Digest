"""Aggregate items from all fetcher sources (blogs, GitHub, Hacker News)."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.constants import THREAD_POOL_WORKERS
from src.fetchers.blog_fetcher import fetch_blog_posts
from src.fetchers.github_fetcher import fetch_github_releases
from src.fetchers.hackernews_fetcher import fetch_hackernews_stories
from src.fetchers.huggingface_fetcher import fetch_huggingface_papers
from src.logger import get_logger

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
        filter_keywords: Optional keyword list for blog relevance filtering

    Returns:
        Combined, deduplicated, and sorted list of items
    """
    fetchers = [
        ("Blogs", lambda: fetch_blog_posts(max_results=10, filter_keywords=filter_keywords)),
        ("GitHub", fetch_github_releases),
        ("Hacker News", fetch_hackernews_stories),
        ("HF Papers", fetch_huggingface_papers),
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

    # Sort by published date (most recent first)
    unique.sort(key=lambda x: x.get("published", ""), reverse=True)

    return unique[:max_results]
