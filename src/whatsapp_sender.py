"""Send WhatsApp messages using Twilio."""

from twilio.rest import Client


def send_whatsapp_message(
    account_sid: str,
    auth_token: str,
    from_number: str,
    to_number: str,
    message: str,
) -> str:
    """
    Send a WhatsApp message using Twilio.

    Args:
        account_sid: Twilio Account SID
        auth_token: Twilio Auth Token
        from_number: Twilio WhatsApp number (format: whatsapp:+14155238886)
        to_number: Recipient WhatsApp number (format: whatsapp:+1234567890)
        message: Message content

    Returns:
        Message SID if successful
    """
    client = Client(account_sid, auth_token)

    sent_message = client.messages.create(
        body=message,
        from_=from_number,
        to=to_number,
    )

    return sent_message.sid


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def format_research_message(research: dict) -> str:
    """
    Format research into a WhatsApp message with ELI5 summary.

    Args:
        research: Research paper dictionary with title, authors, description, url, summary

    Returns:
        Formatted message string (max 1600 chars for WhatsApp)
    """
    if not research:
        return "*Daily AI Research*\n\nNo research found today."

    title = research.get("title", "Untitled")
    authors = _truncate(research.get("authors", "Unknown"), 60)
    source = research.get("source", "Unknown")
    url = research.get("url", "")

    # ELI5 summary is the star - give it plenty of space
    summary = research.get("summary", "")
    if summary:
        summary = _truncate(summary, 600)

    # Build message
    message = f"""*Daily AI Research*

*{title}*
_{authors}_

{summary}

{url}
_Source: {source}_"""

    return message
