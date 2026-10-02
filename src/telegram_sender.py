"""Send Telegram messages using the Bot API."""

import os
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


# Topic id -> Telegram hashtag, mirroring topic_config.DEFAULT_TOPICS.
TOPIC_LABELS = {
    "model_releases": "#ModelRelease",
    "product_api": "#ProductAPI",
    "lab_research": "#LabResearch",
    "agents_tooling": "#Agents",
    "benchmarks": "#Benchmarks",
    "safety_system_cards": "#SafetySystemCards",
    "open_weights": "#OpenWeights",
    "infrastructure": "#Infrastructure",
    "multimodal": "#Multimodal",
    "enterprise_deployment": "#Enterprise",
    "policy_regulation": "#Policy",
}

# Fallback tag when an item carries no topic_id.
TYPE_TAGS = {
    "announcement": "#Announcement",
    "release": "#Release",
    "discussion": "#Discussion",
    "paper": "#Paper",
}

# release_type -> badge shown next to the source.
RELEASE_TYPE_BADGES = {
    "model": "🧠 model",
    "product": "📦 product",
    "api": "🔌 API",
    "research": "📄 research",
    "open-weights": "🔓 open weights",
    "open weights": "🔓 open weights",
    "infrastructure": "⚙️ infrastructure",
    "safety": "🛡 safety",
    "policy": "⚖️ policy",
}

# Structured brief sections rendered into the message, in order.
MESSAGE_SECTIONS = (
    ("what_shipped", "What shipped"),
    ("capabilities", "Capabilities"),
    ("availability", "Availability"),
    ("why_it_matters", "Why it matters"),
    ("caveats", "Caveats"),
)


HEADLINE_LIMIT = int(os.getenv("DIGEST_HEADLINE_LIMIT", "5"))


def _format_headlines(items: list[dict] | None) -> list[str]:
    """Render the runners-up as one line each: title, link, source.

    Returns a list of lines to append, empty when there is nothing to add, so
    a day with a single worthwhile item still reads as a clean brief rather
    than a brief with an empty section under it.
    """
    if not items:
        return []

    lines = ["", "*Also today*"]
    for entry in items[:HEADLINE_LIMIT]:
        title = _escape_markdown((entry.get("title") or "Untitled").strip())
        source = _escape_markdown(entry.get("source", ""))
        link = _validate_url(entry.get("url", ""))
        suffix = f" — {source}" if source else ""
        lines.append(f"• [{title}]({link}){suffix}" if link else f"• {title}{suffix}")
    return lines


def format_digest_message(item: dict, also: list[dict] | None = None) -> str:
    """
    Format the daily digest: one deep brief, then the rest as headlines.

    The pool holds around twenty candidates a day and only the top pick was
    ever shown, so everything else was discarded unseen. "Staying up to date"
    needs the sweep as well as the detail.

    Args:
        item: The top pick, with title, source, url and the structured brief
        also: Further items, already ranked, rendered as one-line headlines

    Returns:
        Formatted message string with Markdown
    """
    if not item:
        return "*AI Dev Digest*\n\nNo updates found today."

    title = _escape_markdown(item.get("title", "Untitled"))
    source = _escape_markdown(item.get("source", "Unknown"))
    url = _validate_url(item.get("url", ""))

    # Build topic tag from topic_id (preferred) or item type fallback
    topic_id = item.get("topic_id", "")
    tag = TOPIC_LABELS.get(topic_id) or TYPE_TAGS.get(item.get("type", ""), "#Update")

    # Release-type badge
    release_type = item.get("release_type", "").lower().strip()
    badge = RELEASE_TYPE_BADGES.get(release_type)
    badge_str = f" · {badge}" if badge else ""

    # Structured brief fields
    sections = [
        (label, _escape_markdown(item.get(key, "")))
        for key, label in MESSAGE_SECTIONS
    ]

    # Fall back to flat summary if the structured brief is missing
    if not any(text for _, text in sections):
        summary = _escape_markdown(item.get("summary", ""))
        flat = f"""{tag} · {source}{badge_str}

*{title}*

{summary}

{url}"""
        return flat + "\n".join(_format_headlines(also))

    lines = [f"{tag} · {source}{badge_str}", "", f"*{title}*"]

    for label, text in sections:
        if text:
            lines += ["", f"*{label}*", text]

    if url:
        lines += ["", url]

    lines += _format_headlines(also)
    return "\n".join(lines)


@retry_with_backoff(exceptions=(requests.RequestException,))
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
