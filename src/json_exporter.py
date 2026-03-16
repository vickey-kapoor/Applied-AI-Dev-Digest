"""JSON export utilities for dashboard data."""

import json
import os
import uuid
from datetime import datetime
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)

# Data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def ensure_data_dir():
    """Ensure the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filename: str) -> dict:
    """Load JSON file from data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in %s, returning empty dict", filename)
        return {}


def save_json(filename: str, data: dict):
    """Save JSON file to data directory."""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved %s", filepath)


def export_papers(research_items: list[dict], ranked_paper: dict = None) -> str:
    """
    Export fetched papers to papers.json.

    Args:
        research_items: List of research items from fetch_ai_research
        ranked_paper: The top-ranked paper (optional, to update ranking score)

    Returns:
        ID of the top paper if ranked_paper provided
    """
    data = load_json("papers.json")
    if "papers" not in data:
        data["papers"] = []

    existing_titles = {p["title"] for p in data["papers"]}
    top_paper_id = None
    now = datetime.utcnow().isoformat() + "Z"

    for item in research_items:
        # Skip if already exists
        if item.get("title") in existing_titles:
            continue

        paper_id = str(uuid.uuid4())

        # Check if this is the ranked paper
        is_top = ranked_paper and item.get("title") == ranked_paper.get("title")
        if is_top:
            top_paper_id = paper_id

        paper = {
            "id": paper_id,
            "title": item.get("title", "Untitled"),
            "description": item.get("description", "")[:1000],  # Truncate long descriptions
            "source": item.get("source", "Unknown"),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", now.split("T")[0]),
            "fetched_at": now,
            "authors": item.get("authors", ""),
            "topics": extract_topics(item),
            "ranking_score": ranked_paper.get("ranking_score", 0) if is_top else 0,
            "status": "unread"
        }

        data["papers"].append(paper)
        existing_titles.add(paper["title"])

    # Sort by fetched_at descending
    data["papers"].sort(key=lambda x: x.get("fetched_at", ""), reverse=True)

    # Keep only last 500 papers to prevent unbounded growth
    data["papers"] = data["papers"][:500]

    save_json("papers.json", data)
    logger.info("Exported %d papers to papers.json", len(research_items))

    return top_paper_id


def extract_topics(item: dict) -> list[str]:
    """Extract topic tags from a product update item."""
    topics = []

    # Add keyword-based topics for developer product features
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()

    topic_keywords = {
        "Model Release": ["model", "gpt", "claude", "gemini", "llama", "mistral", "command"],
        "API Update": ["api", "endpoint", "rest"],
        "SDK/Library": ["sdk", "library", "package", "client"],
        "Fine-tuning": ["fine-tun", "custom model", "training"],
        "Embeddings": ["embedding"],
        "Multimodal": ["vision", "image", "audio", "video", "multimodal"],
        "Developer Tools": ["playground", "cli", "console", "dashboard"],
        "Pricing": ["pricing", "cost", "token", "rate limit"],
        "Function Calling": ["function calling", "tool use", "tool calling"],
    }

    for topic, keywords in topic_keywords.items():
        if any(kw in text for kw in keywords):
            if topic not in topics:
                topics.append(topic)

    return topics[:5]  # Limit to 5 topics


def export_digest(
    top_paper_id: str,
    papers_fetched: int,
    pdf_path: str = None,
    telegram_sent: bool = False,
    workflow_run_id: str = None
):
    """
    Export digest entry to digests.json.

    Args:
        top_paper_id: ID of the top-ranked paper
        papers_fetched: Number of papers fetched
        pdf_path: Path to generated PDF report
        telegram_sent: Whether Telegram message was sent
        workflow_run_id: GitHub Actions run ID (optional)
    """
    data = load_json("digests.json")
    if "digests" not in data:
        data["digests"] = []

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Check if digest for today already exists
    for digest in data["digests"]:
        if digest.get("date") == today:
            # Update existing entry
            digest["top_paper_id"] = top_paper_id
            digest["papers_fetched"] = papers_fetched
            if pdf_path:
                digest["pdf_path"] = pdf_path
            digest["telegram_sent"] = telegram_sent
            if workflow_run_id:
                digest["workflow_run_id"] = workflow_run_id
            save_json("digests.json", data)
            logger.info("Updated digest for %s", today)
            return

    # Create new entry
    digest = {
        "date": today,
        "top_paper_id": top_paper_id or "",
        "papers_fetched": papers_fetched,
        "pdf_path": pdf_path or "",
        "telegram_sent": telegram_sent,
        "workflow_run_id": workflow_run_id or ""
    }

    # Add to beginning of list
    data["digests"].insert(0, digest)

    # Keep only last 90 days
    data["digests"] = data["digests"][:90]

    save_json("digests.json", data)
    logger.info("Exported digest for %s", today)
