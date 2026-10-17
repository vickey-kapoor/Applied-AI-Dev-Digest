"""Fetch trending papers from Hugging Face Daily Papers.

Two things about this API are easy to get wrong, and getting either wrong
makes the source return nothing at all rather than fail:

1. The upvote count lives on the nested `paper` object as `upvotes`. A
   top-level `numUpvotes` key is not present, so reading it yields 0 and
   every paper falls below HF_MIN_UPVOTES. That is what happened here: the
   source contributed zero items on every run while logging a cheerful
   "Found 0 papers".
2. The entry's top-level `publishedAt` is the paper's arXiv date, which runs
   two to four days behind the daily list it appears on, and
   `paper.submittedOnDailyAt` is midnight UTC of the list's own date. Neither
   survives a 24-hour window: by mid-afternoon UTC yesterday's list is over
   40 hours old by that measure, and today's list is not published yet.

So this fetcher no longer carries a recency window of its own. The list is a
single day's selection — asking for that day *is* the recency filter — and
the central DIGEST_MAX_AGE_HOURS cut in fetch_all still bounds how old an
item may be when it reaches the candidate pool.

The daily list is empty until HF publishes the day's selection, so a request
for today can legitimately return []. The previous day is tried in that case.
"""

import json
import urllib.request
from datetime import datetime, timedelta, timezone

from src.constants import HF_MAX_PAPERS, HF_MIN_UPVOTES, REQUEST_TIMEOUT, USER_AGENT
from src.logger import get_logger

logger = get_logger(__name__)

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def _parse_dt(value: str) -> datetime | None:
    """Parse an HF timestamp into aware UTC, or None when it will not parse."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _upvotes(entry: dict, paper: dict) -> int:
    """Read the upvote count from whichever key this response carries."""
    for value in (paper.get("upvotes"), entry.get("numUpvotes")):
        if isinstance(value, int):
            return value
    return 0


def _listed_at(entry: dict, paper: dict) -> datetime | None:
    """When the paper appeared on the daily list, not when it hit arXiv."""
    return _parse_dt(paper.get("submittedOnDailyAt", "")) or _parse_dt(
        entry.get("publishedAt", "")
    )


def _fetch_day(date_str: str) -> list:
    """Fetch one day's list. Returns [] on any failure or unexpected shape."""
    url = f"{HF_DAILY_PAPERS_URL}?date={date_str}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception:
        logger.error("Could not fetch Hugging Face daily papers for %s", date_str)
        return []

    if not isinstance(data, list):
        logger.warning("Unexpected HF daily papers response format for %s", date_str)
        return []
    return data


def fetch_huggingface_papers(filter_keywords: list[str] | None = None) -> list[dict]:
    """Fetch the most recent daily-papers list from Hugging Face.

    Reads today's list, falling back to yesterday's when today's is not
    published yet, and keeps papers with upvotes >= HF_MIN_UPVOTES. When
    filter_keywords is provided, only papers whose title or summary match at
    least one keyword are returned. Returns up to HF_MAX_PAPERS items.
    """
    now = datetime.now(timezone.utc)
    data = _fetch_day(now.strftime("%Y-%m-%d"))
    if not data:
        # Today's list is published some hours into the UTC day; before that
        # the endpoint answers with an empty list rather than an error.
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info("No daily papers listed for today yet — trying %s", yesterday)
        data = _fetch_day(yesterday)

    papers = []

    for entry in data:
        try:
            paper_data = entry.get("paper") or {}
            if not paper_data:
                continue

            upvotes = _upvotes(entry, paper_data)
            if upvotes < HF_MIN_UPVOTES:
                continue

            listed_at = _listed_at(entry, paper_data)

            paper_id = paper_data.get("id", "")
            title = paper_data.get("title", "")
            summary = (paper_data.get("summary", "") or "")[:500]

            if not title:
                continue

            if filter_keywords:
                text = (title + " " + summary).lower()
                if not any(kw.lower() in text for kw in filter_keywords):
                    continue

            papers.append({
                "title": title,
                "summary": summary,
                "url": f"https://huggingface.co/papers/{paper_id}",
                "source": "Hugging Face",
                "upvotes": upvotes,
                "published": (listed_at or now).isoformat(),
                "type": "paper",
            })
        except (AttributeError, KeyError, TypeError, ValueError):
            continue

    # Sort by upvotes descending, take top N
    papers.sort(key=lambda x: x.get("upvotes", 0), reverse=True)
    result = papers[:HF_MAX_PAPERS]
    logger.info("Found %d papers from Hugging Face Daily Papers", len(result))
    return result
