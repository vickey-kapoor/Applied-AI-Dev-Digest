"""Generate a digest preview without sending to Telegram. Outputs JSON to stdout."""

import json
import os
import sys

from dotenv import load_dotenv

from src.constants import DIGEST_MAX_RESULTS
from src.topic_config import get_active_keywords
from src.fetcher import fetch_all
from src.news_ranker import rank_news
from src.news_summarizer import summarize_release
from src.logger import get_logger

logger = get_logger(__name__)


def main():
    load_dotenv()

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        json.dump({"error": "OPENAI_API_KEY not set"}, sys.stdout)
        sys.exit(1)

    active_keywords = get_active_keywords()

    # Fetch
    try:
        items = fetch_all(max_results=DIGEST_MAX_RESULTS, filter_keywords=active_keywords)
    except Exception as e:
        json.dump({"error": f"Fetch failed: {e}"}, sys.stdout)
        sys.exit(1)

    if not items:
        json.dump({"error": "No items found"}, sys.stdout)
        sys.exit(0)

    # Rank
    try:
        top = rank_news(items, openai_key) or items[0]
    except Exception:
        top = items[0]

    # Summarize
    try:
        top = summarize_release(top, openai_key)
    except Exception:
        pass  # Summary is optional for preview

    # Output JSON
    result = {
        "title": top.get("title", ""),
        "source": top.get("source", ""),
        "url": top.get("url", ""),
        "type": top.get("type", ""),
        "summary": top.get("summary", ""),
        "what_shipped": top.get("what_shipped", ""),
        "capabilities": top.get("capabilities", ""),
        "availability": top.get("availability", ""),
        "why_it_matters": top.get("why_it_matters", ""),
        "caveats": top.get("caveats", ""),
        "release_type": top.get("release_type", ""),
        "detailed_summary": top.get("detailed_summary", ""),
        "topic_id": top.get("topic_id", ""),
    }
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
