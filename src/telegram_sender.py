"""Send Telegram messages using the Bot API."""

import re
from urllib.parse import urlparse

import requests

from src.constants import TELEGRAM_API_URL, TELEGRAM_MAX_MESSAGE_LENGTH
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

MARKDOWN_SPECIAL_CHARS = "\\_*[]()`"


def _validate_url(url: str) -> str:
    """
    Validate and sanitize URL.

    Returns empty string if URL is invalid or potentially malicious.
    """
    if not url or not isinstance(url, str):
        return ""

    url = url.strip()

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ""
        if not parsed.netloc:
            return ""
    except Exception:
        return ""

    suspicious_patterns = [
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'<script',
        r'onclick',
        r'onerror',
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return ""

    return url


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def _truncate_message(message: str) -> str:
    """Truncate message to Telegram's maximum message length."""
    if len(message) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        return message
    return message[: TELEGRAM_MAX_MESSAGE_LENGTH - 3].rsplit("\n", 1)[0] + "..."


def _escape_markdown(text: str) -> str:
    """Escape Telegram Markdown special characters in user-controlled text."""
    if not text:
        return ""

    escaped = text
    for char in MARKDOWN_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def format_research_message(research: dict) -> str:
    """
    Format item into a Telegram message using the structured dev digest format.

    Args:
        research: Item dictionary with title, source, url, and structured summary fields

    Returns:
        Formatted message string with Markdown
    """
    if not research:
        return "*Applied AI Dev Digest*\n\nNo updates found today."

    title = _escape_markdown(research.get("title", "Untitled"))
    source = _escape_markdown(research.get("source", "Unknown"))
    url = _validate_url(research.get("url", ""))

    # Build topic tag from topic_id (preferred) or item type fallback
    topic_id = research.get("topic_id", "")
    topic_labels = {
        "computer_use": "#ComputerUse",
        "models": "#Models",
        "apis": "#APIs",
        "frameworks": "#Frameworks",
        "inference": "#Inference",
        "finetuning": "#FineTuning",
        "rag": "#RAG",
        "agents": "#Agents",
        "opensource": "#OpenSource",
        "safety": "#Safety",
        "hardware": "#Hardware",
    }
    type_tags = {"announcement": "#Announcement", "release": "#Release", "discussion": "#Discussion"}
    tag = topic_labels.get(topic_id) or type_tags.get(research.get("type", ""), "#Update")

    # Effort indicator
    effort_map = {"low": "🟢", "medium": "🟡", "high": "🔴"}
    effort_label = {"low": "quick win", "medium": "afternoon project", "high": "deep dive"}
    effort = research.get("effort", "").lower().strip()
    effort_str = f" · {effort_map[effort]} {effort_label[effort]}" if effort in effort_map else ""

    # Structured summary fields
    why = _escape_markdown(research.get("why_it_matters", ""))
    what = _escape_markdown(research.get("what_it_is", ""))
    how = _escape_markdown(research.get("how_to_use_it", ""))
    take = _escape_markdown(research.get("dev_take", ""))

    # Fall back to flat summary if structured fields are missing
    if not why and not what:
        summary = _escape_markdown(research.get("summary", ""))
        message = f"""{tag} · {source}{effort_str}

*{title}*

{summary}

{url}"""
        return message

    lines = [f"{tag} · {source}{effort_str}", "", f"*{title}*"]

    if why:
        lines += ["", "*Why it matters*", why]
    if what:
        lines += ["", "*What it is*", what]
    if how:
        lines += ["", "*How to use it*", how]
    if take:
        lines += ["", "*Dev take*", take]

    if url:
        lines += ["", url]

    return "\n".join(lines)


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(requests.RequestException,))
def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Send a message via Telegram Bot API.

    Args:
        bot_token: Telegram bot token from BotFather
        chat_id: Target chat ID
        message: Message content (supports Markdown)

    Returns:
        True if message was sent successfully
    """
    message = _truncate_message(message)
    url = TELEGRAM_API_URL.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()

    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")

    logger.info("Telegram message sent to chat %s", chat_id)
    return True
