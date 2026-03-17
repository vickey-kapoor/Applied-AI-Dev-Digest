"""Main entry point for AI Dev Digest."""

import os
import sys

from dotenv import load_dotenv

from src.logger import get_logger
from src.research_fetcher import fetch_ai_research
from src.news_ranker import rank_research
from src.news_summarizer import summarize_research_bundle
from src.telegram_sender import format_research_message, send_telegram_message
from src.pdf_generator import generate_research_pdf
from src.json_exporter import export_papers, export_digest

logger = get_logger(__name__)


def main():
    """Fetch AI product updates, select the most important, and send to Telegram."""
    # Load environment variables
    load_dotenv()

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

    # Fetch product updates from AI labs
    logger.info("Fetching product updates from AI labs...")
    research_items = []
    try:
        research_items = fetch_ai_research(max_results=10)
        logger.info("Found %d product updates", len(research_items))
    except Exception as e:
        logger.error("Error fetching updates: %s", e)

    # Check if we have any content
    if not research_items:
        logger.info("No product updates found today")
        sys.exit(0)

    # Rank and select top update
    logger.info("Selecting most important update...")
    try:
        top_research = rank_research(research_items, openai_key)
        logger.info("Selected: %s", top_research["title"])
    except Exception as e:
        logger.error("Error ranking updates: %s", e)
        top_research = research_items[0]

    # Export updates to JSON for dashboard
    logger.info("Exporting updates to JSON...")
    top_paper_id = None
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

    # Generate PDF report
    logger.info("Generating PDF report...")
    pdf_path = None
    try:
        pdf_path = generate_research_pdf(top_research)
        logger.info("PDF saved: %s", pdf_path)
    except Exception:
        logger.warning("Could not generate PDF")

    # Send Telegram message
    logger.info("Sending Telegram message...")
    telegram_sent = False
    try:
        message = format_research_message(top_research)
        send_telegram_message(telegram_token, telegram_chat_id, message)
        telegram_sent = True
    except Exception as e:
        logger.error("Error sending Telegram message: %s", e)

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

    if not telegram_sent:
        sys.exit(1)


if __name__ == "__main__":
    main()
