"""Main entry point for AI News WhatsApp Alert."""

import os
import sys

from dotenv import load_dotenv

from src.news_fetcher import fetch_ai_news, format_article
from src.news_ranker import rank_news_with_ai, rank_news_simple
from src.whatsapp_sender import format_news_message, send_whatsapp_message


def main():
    """Fetch AI news, select the most important, and send to WhatsApp."""
    # Load environment variables
    load_dotenv()

    # Get required environment variables
    news_api_key = os.getenv("NEWS_API_KEY")
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")
    your_whatsapp = os.getenv("YOUR_WHATSAPP_NUMBER")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Validate required variables
    missing = []
    if not news_api_key:
        missing.append("NEWS_API_KEY")
    if not twilio_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not twilio_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not twilio_whatsapp:
        missing.append("TWILIO_WHATSAPP_NUMBER")
    if not your_whatsapp:
        missing.append("YOUR_WHATSAPP_NUMBER")

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    print("Fetching AI news...")
    try:
        raw_articles = fetch_ai_news(news_api_key, max_articles=10)
        articles = [format_article(a) for a in raw_articles]
        print(f"Found {len(articles)} articles")
    except Exception as e:
        print(f"Error fetching news: {e}")
        sys.exit(1)

    if not articles:
        print("No AI news found today")
        sys.exit(0)

    print("Selecting most important news...")
    try:
        if openai_key:
            top_article = rank_news_with_ai(articles, openai_key)
            print("Used AI ranking")
        else:
            top_article = rank_news_simple(articles)
            print("Used simple ranking (no OpenAI key)")
    except Exception as e:
        print(f"Error ranking news: {e}")
        top_article = articles[0]

    print(f"Selected: {top_article['title']}")

    print("Sending WhatsApp message...")
    try:
        message = format_news_message(top_article)
        message_sid = send_whatsapp_message(
            twilio_sid,
            twilio_token,
            twilio_whatsapp,
            your_whatsapp,
            message,
        )
        print(f"Message sent successfully! SID: {message_sid}")
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
