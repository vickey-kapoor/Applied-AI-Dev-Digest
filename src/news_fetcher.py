"""Fetch AI news from NewsAPI."""

import os
from datetime import datetime, timedelta
from typing import Optional

import requests


def fetch_ai_news(api_key: str, max_articles: int = 10) -> list[dict]:
    """
    Fetch recent AI-related news articles from NewsAPI.

    Args:
        api_key: NewsAPI API key
        max_articles: Maximum number of articles to fetch

    Returns:
        List of article dictionaries
    """
    url = "https://newsapi.org/v2/everything"

    # Get news from the last 24 hours
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    params = {
        "q": "(artificial intelligence OR AI OR machine learning OR ChatGPT OR OpenAI OR Google AI OR Claude OR LLM)",
        "from": yesterday,
        "sortBy": "relevancy",
        "language": "en",
        "pageSize": max_articles,
        "apiKey": api_key,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if data.get("status") != "ok":
        raise ValueError(f"NewsAPI error: {data.get('message', 'Unknown error')}")

    return data.get("articles", [])


def format_article(article: dict) -> dict:
    """Extract relevant fields from an article."""
    return {
        "title": article.get("title", "No title"),
        "description": article.get("description", "No description"),
        "source": article.get("source", {}).get("name", "Unknown"),
        "url": article.get("url", ""),
        "published_at": article.get("publishedAt", ""),
    }
