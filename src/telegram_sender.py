"""Send Telegram messages using the Bot API."""

import re
from urllib.parse import urlparse

import requests

from src.logger import get_logger

logger = get_logger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
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
    Format product update into a Telegram message.

    Args:
        research: Product update dictionary with title, source, description, url, summary

    Returns:
        Formatted message string with Markdown
    """
    if not research:
        return "*Daily AI Dev Digest*\n\nNo updates found today."

    title = _escape_markdown(research.get("title", "Untitled"))
    source = _escape_markdown(research.get("source", "Unknown"))
    url = _validate_url(research.get("url", ""))
    summary = _escape_markdown(research.get("summary", ""))

    message = f"""*Daily AI Dev Digest*

*{title}*

{summary}

{url}
_Lab: {source}_"""

    return message


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
    url = TELEGRAM_API.format(token=bot_token)
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
