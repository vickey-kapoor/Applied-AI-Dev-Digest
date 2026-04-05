"""Generate a digest preview without sending to Telegram. Outputs JSON to stdout."""

import json
import os
import sys

from dotenv import load_dotenv

from src.constants import DIGEST_MAX_RESULTS
from src.topic_config import get_active_keywords
from src.research_fetcher import fetch_ai_research
from src.news_ranker import rank_research
from src.news_summarizer import summarize_research_bundle
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
        items = fetch_ai_research(max_results=DIGEST_MAX_RESULTS, filter_keywords=active_keywords)
    except Exception as e:
        json.dump({"error": f"Fetch failed: {e}"}, sys.stdout)
        sys.exit(1)

    if not items:
        json.dump({"error": "No product updates found"}, sys.stdout)
        sys.exit(0)

    # Rank
    try:
        top = rank_research(items, openai_key)
    except Exception:
        top = items[0]

    # Summarize
    try:
        top = summarize_research_bundle(top, openai_key)
    except Exception:
        pass  # Summary is optional for preview

    # Output JSON
    result = {
        "title": top.get("title", ""),
        "authors": top.get("authors", ""),
        "source": top.get("source", ""),
        "url": top.get("url", ""),
        "summary": top.get("summary", ""),
        "detailed_summary": top.get("detailed_summary", ""),
        "description": top.get("description", ""),
        "topic_id": top.get("topic_id", ""),
    }
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
