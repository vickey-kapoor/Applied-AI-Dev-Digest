"""Aggregate developer product updates from AI lab sources."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from difflib import SequenceMatcher
from typing import Callable

from src.constants import DEDUP_SIMILARITY_THRESHOLD
from src.fetchers.blog_fetcher import fetch_blog_posts
from src.logger import get_logger

logger = get_logger(__name__)


def _title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity ratio between two titles."""
    return SequenceMatcher(
        None,
        title1.lower().strip(),
        title2.lower().strip(),
    ).ratio()


def _deduplicate_papers(papers: list[dict], threshold: float = DEDUP_SIMILARITY_THRESHOLD) -> list[dict]:
    """
    Remove duplicate items based on title similarity.

    Args:
        papers: List of item dictionaries
        threshold: Similarity threshold for considering items as duplicates

    Returns:
        Deduplicated list of items
    """
    if not papers:
        return []

    unique_papers = []
    for paper in papers:
        title = paper.get("title", "")
        is_duplicate = False

        for existing in unique_papers:
            existing_title = existing.get("title", "")
            if _title_similarity(title, existing_title) >= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_papers.append(paper)

    return unique_papers


def fetch_ai_research(max_results: int = 5) -> list[dict]:
    """
    Fetch developer product updates from all AI lab sources in parallel.

    Args:
        max_results: Maximum number of items to return

    Returns:
        Combined, deduplicated, and sorted list of product updates
    """
    fetchers: list[tuple[str, Callable, int]] = [
        ("Blogs", fetch_blog_posts, 10),
    ]

    all_research = []

    # Fetch from all sources in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_source = {
            executor.submit(fetcher, count): source
            for source, fetcher, count in fetchers
        }

        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                results = future.result()
                logger.info("Fetched %d items from %s", len(results), source)
                all_research.extend(results)
            except Exception:
                logger.error("Failed to fetch from %s", source)

    # Deduplicate by title similarity
    unique_research = _deduplicate_papers(all_research)
    logger.info("After deduplication: %d unique items", len(unique_research))

    # Sort by published date (most recent first)
    unique_research.sort(
        key=lambda x: x.get("published_at", ""),
        reverse=True,
    )

    return unique_research[:max_results]
