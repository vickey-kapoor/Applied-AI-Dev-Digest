"""Rank AI news by importance using OpenAI."""

import json
from typing import Optional

from openai import OpenAI


def rank_news_with_ai(articles: list[dict], api_key: str) -> dict:
    """
    Use OpenAI to select the most important AI news article.

    Args:
        articles: List of article dictionaries
        api_key: OpenAI API key

    Returns:
        The most important article
    """
    if not articles:
        raise ValueError("No articles to rank")

    if len(articles) == 1:
        return articles[0]

    client = OpenAI(api_key=api_key)

    # Prepare articles summary for the prompt
    articles_text = "\n\n".join(
        f"[{i+1}] Title: {a['title']}\nSource: {a['source']}\nDescription: {a['description']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are an AI news curator. Analyze these AI/ML news articles and select the ONE most important and impactful news story.

Consider these factors:
1. Significance to the AI industry (major breakthroughs, releases, regulations)
2. Impact on everyday users and businesses
3. Credibility of the source
4. Novelty (prefer breaking news over ongoing stories)

Articles:
{articles_text}

Respond with ONLY the number of the most important article (e.g., "1" or "5"). No explanation needed."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0,
    )

    try:
        selected_index = int(response.choices[0].message.content.strip()) - 1
        if 0 <= selected_index < len(articles):
            return articles[selected_index]
    except (ValueError, IndexError):
        pass

    # Fallback to first article if parsing fails
    return articles[0]


def rank_news_simple(articles: list[dict]) -> dict:
    """
    Simple ranking without AI - returns the first article (most relevant by NewsAPI).

    Args:
        articles: List of article dictionaries

    Returns:
        The first article (assumed most relevant)
    """
    if not articles:
        raise ValueError("No articles to rank")
    return articles[0]
