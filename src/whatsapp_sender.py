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


def format_news_message(article: dict) -> str:
    """
    Format an article into a WhatsApp message.

    Args:
        article: Article dictionary with title, description, source, url

    Returns:
        Formatted message string
    """
    message = f"""🤖 *Daily AI News Alert*

📰 *{article['title']}*

📝 {article['description']}

🔗 {article['url']}

_Source: {article['source']}_
"""
    return message
