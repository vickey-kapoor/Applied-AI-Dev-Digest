"""Main entry point for AI Dev Digest."""

import os
import sys

from dotenv import load_dotenv

from datetime import datetime, timezone

from src.constants import DIGEST_MAX_RESULTS
from src.logger import get_logger
from src.topic_config import get_active_keywords, is_paused, increment_topic_stat
from src.research_fetcher import fetch_ai_research
from src.news_ranker import rank_research
from src.news_summarizer import summarize_research_bundle
from src.telegram_sender import format_research_message, send_telegram_message
from src.pdf_generator import generate_research_pdf
from src.json_exporter import export_papers, export_digest, get_sent_top_paper_ids, _paper_id_for_item
from src.kv_client import kv_append, kv_set

logger = get_logger(__name__)


def main():
    """Fetch AI product updates, select the most important, and send to Telegram."""
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

    # Fetch product updates from AI labs
    logger.info("Fetching product updates from AI labs...")
    research_items = []
    try:
        research_items = fetch_ai_research(max_results=DIGEST_MAX_RESULTS, filter_keywords=active_keywords)
        logger.info("Found %d product updates", len(research_items))
    except Exception as e:
        logger.error("Error fetching updates: %s", e)

    # Check if we have any content
    if not research_items:
        logger.info("No product updates found today")
        sys.exit(0)

    # Filter out papers already sent as top pick
    sent_ids = get_sent_top_paper_ids()
    new_items = [item for item in research_items if _paper_id_for_item(item) not in sent_ids]
    if new_items:
        logger.info("Filtered out %d already-sent papers", len(research_items) - len(new_items))
    else:
        logger.info("All %d papers were previously sent, skipping digest", len(research_items))

    # Export all fetched papers to JSON (even if already sent)
    # Rank and select top update
    logger.info("Selecting most important update...")
    try:
        top_research = rank_research(items_for_ranking, openai_key)
        logger.info("Selected: %s", top_research["title"])
    except Exception as e:
        logger.error("Error ranking updates: %s", e)
        top_research = research_items[0]

    # Track topic stats in KV
    try:
        topic_id = top_research.get("topic_id")
        if topic_id:
            increment_topic_stat(topic_id)
    except Exception as e:
        logger.warning("Could not update topic stats: %s", e)

    # Append top paper to weekly KV list for Sunday digest
    try:
        kv_append("digest:weekly", {
            "title": top_research.get("title", ""),
            "authors": top_research.get("authors", ""),
            "institution": top_research.get("institution"),
            "topic_id": top_research.get("topic_id"),
            "url": top_research.get("url", ""),
            "why_it_matters": top_research.get("summary", ""),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        })
        logger.info("Appended top paper to weekly KV list")
    except Exception as e:
        logger.warning("Could not append to weekly KV: %s", e)

    # Export updates to JSON for dashboard
    logger.info("Exporting updates to JSON...")
    top_paper_id = None
    top_research = None

    if new_items:
        # Rank and select top update from unsent papers only
        logger.info("Selecting most important update...")
        try:
            top_research = rank_research(new_items, openai_key)
            logger.info("Selected: %s", top_research["title"])
        except Exception as e:
            logger.error("Error ranking updates: %s", e)
            top_research = new_items[0]

        try:
            top_paper_id = export_papers(research_items, top_research)
            logger.info("Papers exported to data/papers.json")
        except Exception as e:
            logger.warning("Could not export papers to JSON: %s", e)

        # Generate summaries in one model call
        logger.info("Generating summaries...")
        try:
            top_research = summarize_research_bundle(top_research, openai_key)
            if "summary" in top_research:
                logger.info("Generated short summary")
            if "detailed_summary" in top_research:
                logger.info("Generated detailed summary for PDF")
        except Exception:
            logger.warning("Could not generate summaries")
    else:
        # Still export papers for the dashboard, but no top pick
        try:
            export_papers(research_items)
            logger.info("Papers exported to data/papers.json")
        except Exception as e:
            logger.warning("Could not export papers to JSON: %s", e)

    # Generate PDF report
    pdf_path = None
    if top_research:
        logger.info("Generating PDF report...")
        try:
            pdf_path = generate_research_pdf(top_research)
            logger.info("PDF saved: %s", pdf_path)
        except Exception:
            logger.warning("Could not generate PDF")

    # Send Telegram message (only if we have a new paper to send)
    telegram_sent = False
    if top_research:
        logger.info("Sending Telegram message...")
        try:
            message = format_research_message(top_research)
            send_telegram_message(telegram_token, telegram_chat_id, message)
            telegram_sent = True
        except Exception as e:
            logger.error("Error sending Telegram message: %s", e)

    # Store last sent paper payload in KV for test-send
    if telegram_sent:
        try:
            kv_set("digest:last", {
                "title": top_research.get("title", ""),
                "authors": top_research.get("authors", ""),
                "source": top_research.get("source", ""),
                "url": top_research.get("url", ""),
                "summary": top_research.get("summary", ""),
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
            papers_fetched=len(research_items),
            pdf_path=pdf_path,
            telegram_sent=telegram_sent,
            workflow_run_id=workflow_run_id
        )
        logger.info("Digest exported to data/digests.json")
    except Exception as e:
        logger.warning("Could not export digest to JSON: %s", e)


if __name__ == "__main__":
    main()
