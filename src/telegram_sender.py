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
    Format item into a Telegram message using the safety-research digest format.

    Args:
        research: Item dictionary with title, source, url, and structured summary fields

    Returns:
        Formatted message string with Markdown
    """
    if not research:
        return "*AI Safety Digest*\n\nNo updates found today."

    title = _escape_markdown(research.get("title", "Untitled"))
    source = _escape_markdown(research.get("source", "Unknown"))
    url = _validate_url(research.get("url", ""))

    # Build topic tag from topic_id (preferred) or item type fallback
    topic_id = research.get("topic_id", "")
    topic_labels = {
        "alignment": "#Alignment",
        "interpretability": "#Interpretability",
        "evals": "#Evals",
        "red_teaming": "#RedTeaming",
        "system_cards": "#SystemCards",
        "agentic_safety": "#AgenticSafety",
        "governance": "#Governance",
        "catastrophic_risk": "#CatastrophicRisk",
        "robustness": "#Robustness",
        "data_provenance": "#DataProvenance",
        "open_weights_safety": "#OpenWeightsSafety",
    }
    type_tags = {"announcement": "#Announcement", "release": "#Release", "discussion": "#Discussion", "paper": "#Paper"}
    tag = topic_labels.get(topic_id) or type_tags.get(research.get("type", ""), "#Update")

    # Rigor indicator (replaces "effort")
    rigor_map = {
        "preprint": "📄 preprint",
        "peer-reviewed": "🎓 peer-reviewed",
        "peer reviewed": "🎓 peer-reviewed",
        "lab-blog": "🏛 lab blog",
        "lab blog": "🏛 lab blog",
        "position": "💭 position",
        "system-card": "📋 system card",
        "system card": "📋 system card",
    }
    rigor = research.get("rigor", "").lower().strip()
    rigor_str = f" · {rigor_map[rigor]}" if rigor in rigor_map else ""

    # Structured summary fields
    claim = _escape_markdown(research.get("claim", ""))
    evidence = _escape_markdown(research.get("evidence", ""))
    method = _escape_markdown(research.get("method", ""))
    limitations = _escape_markdown(research.get("limitations", ""))
    safety_rel = _escape_markdown(research.get("safety_relevance", ""))

    # Fall back to flat summary if structured fields are missing
    if not claim and not evidence:
        summary = _escape_markdown(research.get("summary", ""))
        message = f"""{tag} · {source}{rigor_str}

*{title}*

{summary}

{url}"""
        return message

    lines = [f"{tag} · {source}{rigor_str}", "", f"*{title}*"]

    if claim:
        lines += ["", "*Claim*", claim]
    if evidence:
        lines += ["", "*Evidence*", evidence]
    if method:
        lines += ["", "*Method*", method]
    if limitations:
        lines += ["", "*Limitations*", limitations]
    if safety_rel:
        lines += ["", "*Safety relevance*", safety_rel]

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
