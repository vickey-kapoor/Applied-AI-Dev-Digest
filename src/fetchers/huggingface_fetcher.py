"""Fetch trending papers from Hugging Face Daily Papers."""

import json
import urllib.request
from datetime import datetime, timedelta, timezone

from src.constants import HF_MAX_PAPERS, HF_MIN_UPVOTES, REQUEST_TIMEOUT
from src.logger import get_logger

logger = get_logger(__name__)

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def fetch_huggingface_papers() -> list[dict]:
    """Fetch today's top papers from Hugging Face Daily Papers.

    Filters to papers published within the last 24 hours with upvotes >= HF_MIN_UPVOTES.
    Returns up to HF_MAX_PAPERS items.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{HF_DAILY_PAPERS_URL}?date={today}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AI-Dev-Digest"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception:
        logger.error("Could not fetch Hugging Face daily papers")
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected HF daily papers response format")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    papers = []

    for entry in data:
        try:
            upvotes = entry.get("numUpvotes", 0)
            if upvotes < HF_MIN_UPVOTES:
                continue

            published_str = entry.get("publishedAt", "")
            if published_str:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                if published_dt < cutoff:
                    continue

            paper_data = entry.get("paper", {})
            if not paper_data:
                continue

            paper_id = paper_data.get("id", "")
            title = paper_data.get("title", "")
            summary = (paper_data.get("summary", "") or "")[:500]

            if not title:
                continue

            papers.append({
                "title": title,
                "summary": summary,
                "url": f"https://huggingface.co/papers/{paper_id}",
                "source": "Hugging Face",
                "upvotes": upvotes,
                "published": published_str,
                "type": "paper",
            })
        except (KeyError, TypeError, ValueError):
            continue

    # Sort by upvotes descending, take top N
    papers.sort(key=lambda x: x.get("upvotes", 0), reverse=True)
    result = papers[:HF_MAX_PAPERS]
    logger.info("Found %d papers from Hugging Face Daily Papers", len(result))
    return result
