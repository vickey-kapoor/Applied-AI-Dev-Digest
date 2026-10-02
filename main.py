"""Main entry point for Applied AI Dev Digest."""

import os
import sys

from dotenv import load_dotenv

from datetime import datetime, timezone

from src.constants import DIGEST_MAX_RESULTS, HISTORY_MAX_ENTRIES
from src.logger import get_logger
from src.topic_config import get_active_keywords, is_paused, increment_topic_stat
from src.fetcher import fetch_all
from src.news_ranker import rank_news_ranked
from src.article_fetcher import fetch_article_text
from src.news_summarizer import summarize_release
from src.telegram_sender import format_digest_message, send_telegram_message
from src.pdf_generator import generate_digest_pdf
from src.json_exporter import export_papers, export_digest, get_sent_top_paper_ids, _paper_id_for_item
from src.kv_client import kv_append, kv_set, kv_trim_to_last

logger = get_logger(__name__)


def main():
    """Fetch AI lab developments, select the most significant, and send to Telegram."""
    # Load environment variables
    load_dotenv()

    # Check if digest is paused
    if is_paused():
        logger.info("Digest is paused — exiting")
        sys.exit(0)

    # Get required environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Validate required variables
    missing = []
    if not openai_key:
        missing.append("OPENAI_API_KEY")
    if not telegram_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    # Load active topic keywords
    active_keywords = get_active_keywords()
    logger.info("Active topic keywords: %d", len(active_keywords))

    # Fetch items from all sources (blogs, GitHub releases, Hacker News)
    logger.info("Fetching AI lab development items...")
    items = []
    try:
        items = fetch_all(max_results=DIGEST_MAX_RESULTS, filter_keywords=active_keywords)
        logger.info("Found %d items from all sources", len(items))
    except Exception as e:
        logger.error("Error fetching items: %s", e)

    # Check if we have any content
    if not items:
        # Record the empty day rather than exiting silently — otherwise the
        # commit step stages nothing and the day vanishes from digests.json
        # with no way to tell it apart from a run that never fired.
        logger.info("No items found today")
        try:
            export_digest(
                top_paper_id=None,
                papers_fetched=0,
                pdf_path=None,
                telegram_sent=False,
                workflow_run_id=os.getenv("GITHUB_RUN_ID", ""),
            )
            logger.info("Recorded empty digest in data/digests.json")
        except Exception as e:
            logger.warning("Could not record empty digest: %s", e)
        sys.exit(0)

    # Filter out papers already sent as top pick
    sent_ids = get_sent_top_paper_ids()
    new_items = [item for item in items if _paper_id_for_item(item) not in sent_ids]
    if new_items:
        logger.info("Filtered out %d already-sent items", len(items) - len(new_items))
    else:
        logger.info("All %d items were previously sent, skipping digest", len(items))

    # Export all fetched items to JSON and select top pick
    top_paper_id = None
    top_item = None
    headlines: list[dict] = []

    if new_items:
        # Rank and select top item from unsent items only
        logger.info("Screening and ranking %d candidates...", len(new_items))
        try:
            ranked = rank_news_ranked(new_items, openai_key)
            if ranked:
                top_item = ranked[0]
                headlines = ranked[1:]
                logger.info("Selected: %s", top_item["title"])
            else:
                # The model judged nothing here worth sending. Honour that: a
                # skipped day beats a padded one, and tomorrow's run retries.
                logger.info("Model rejected all %d candidates — sending nothing", len(new_items))
        except Exception as e:
            logger.error("Error ranking items: %s", e)
            top_item = new_items[0]
            headlines = new_items[1:]

        # Track topic stats in KV
        try:
            topic_id = top_item.get("topic_id")
            if topic_id:
                increment_topic_stat(topic_id)
        except Exception as e:
            logger.warning("Could not update topic stats: %s", e)

        # Generate summaries in one model call. This must run before both the
        # papers.json export and the history-KV append so each saved entry
        # includes the structured fields rather than the raw RSS description.
        logger.info("Generating summaries...")
        try:
            # Open the link first. The feed blurb averaged 273 characters and
            # was sometimes empty, so the brief was being written from a title.
            # Unless the fetcher already supplied the text: OpenAI's changelog
            # arrives as one entry per item, and opening its URL would replace
            # that with all 170-odd entries on the page.
            if not (top_item.get("article_text") or "").strip():
                article = fetch_article_text(top_item.get("url", ""))
                if article:
                    top_item = {**top_item, "article_text": article}
            top_item = summarize_release(top_item, openai_key)
            if "what_shipped" in top_item:
                logger.info("Generated structured brief")
            if "detailed_summary" in top_item:
                logger.info("Generated detailed summary for PDF")
        except Exception:
            logger.warning("Could not generate summaries")

        # summarize_release returns a copy, so swap it back into the
        # fetched list — otherwise papers.json stores the unsummarized original.
        items = [
            top_item if _paper_id_for_item(item) == _paper_id_for_item(top_item) else item
            for item in items
        ]

        try:
            top_paper_id = export_papers(items, top_item)
            logger.info("Items exported to data/papers.json")
        except Exception as e:
            logger.warning("Could not export items to JSON: %s", e)

        # Append the top item to the KV list the dashboard's History page
        # reads. The key name is historical: it fed the Sunday roundup, which
        # also cleared it. Renaming it would orphan the entries already stored.
        try:
            kv_append("digest:weekly", {
                "title": top_item.get("title", ""),
                "source": top_item.get("source", ""),
                "topic_id": top_item.get("topic_id"),
                "url": top_item.get("url", ""),
                "type": top_item.get("type", ""),
                "what_shipped": top_item.get("what_shipped", ""),
                "why_it_matters": top_item.get("why_it_matters", ""),
                "release_type": top_item.get("release_type", ""),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            logger.info("Appended top item to the KV history list")
            # Trimmed on every append rather than on a schedule, so there is
            # no second job to lose.
            kv_trim_to_last("digest:weekly", HISTORY_MAX_ENTRIES)
        except Exception as e:
            logger.warning("Could not append to the KV history list: %s", e)
    else:
        # Still export items for the dashboard, but no top pick
        try:
            export_papers(items)
            logger.info("Items exported to data/papers.json")
        except Exception as e:
            logger.warning("Could not export items to JSON: %s", e)

    # Generate PDF report
    pdf_path = None
    if top_item:
        logger.info("Generating PDF report...")
        try:
            pdf_path = generate_digest_pdf(top_item)
            logger.info("PDF saved: %s", pdf_path)
        except Exception:
            logger.warning("Could not generate PDF")

    # Send Telegram message (only if we have a new item to send)
    telegram_sent = False
    if top_item:
        logger.info("Sending Telegram message...")
        try:
            message = format_digest_message(top_item, also=headlines)
            send_telegram_message(telegram_token, telegram_chat_id, message)
            telegram_sent = True
        except Exception as e:
            logger.error("Error sending Telegram message: %s", e)

    # Store last sent item payload in KV for test-send
    if telegram_sent:
        try:
            kv_set("digest:last", {
                "title": top_item.get("title", ""),
                "source": top_item.get("source", ""),
                "url": top_item.get("url", ""),
                "type": top_item.get("type", ""),
                "topic_id": top_item.get("topic_id", ""),
                "summary": top_item.get("summary", ""),
                "what_shipped": top_item.get("what_shipped", ""),
                "capabilities": top_item.get("capabilities", ""),
                "availability": top_item.get("availability", ""),
                "why_it_matters": top_item.get("why_it_matters", ""),
                "caveats": top_item.get("caveats", ""),
                "release_type": top_item.get("release_type", ""),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })
            logger.info("Stored last digest payload in KV")
        except Exception as e:
            logger.warning("Could not store digest:last in KV: %s", e)

    # Export digest entry to JSON for dashboard
    logger.info("Exporting digest to JSON...")
    try:
        workflow_run_id = os.getenv("GITHUB_RUN_ID", "")
        export_digest(
            top_paper_id=top_paper_id,
            papers_fetched=len(items),
            pdf_path=pdf_path,
            telegram_sent=telegram_sent,
            workflow_run_id=workflow_run_id
        )
        logger.info("Digest exported to data/digests.json")
    except Exception as e:
        logger.warning("Could not export digest to JSON: %s", e)


if __name__ == "__main__":
    main()
