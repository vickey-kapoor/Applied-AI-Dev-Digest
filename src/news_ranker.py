"""Rank AI/dev news by relevance to working ML engineers using OpenAI."""

import json

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.constants import OPENAI_MODEL, OPENAI_MAX_TOKENS_RANKING
from src.logger import get_logger
from src.topic_config import get_feedback_weights
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)
_sanitize_text = sanitize_prompt_text


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(Exception,))
def _call_openai_ranking(client: OpenAI, prompt: str):
    """Make an OpenAI API call for ranking with retry logic."""
    return client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENAI_MAX_TOKENS_RANKING,
        temperature=0,
    )


def rank_research(research: list[dict], api_key: str) -> dict:
    """
    Use OpenAI to select the most important AI product update for developers.

    Args:
        research: List of product update dictionaries
        api_key: OpenAI API key

    Returns:
        The most important product update
    """
    if not research:
        raise ValueError("No research to rank")

    if len(research) == 1:
        return research[0]

    # Load feedback weights and reorder by preference before sending to LLM
    try:
        weights = get_feedback_weights()
        if weights:
            # Sort papers so preferred topics come first (higher weight = earlier)
            research = sorted(
                research,
                key=lambda r: weights.get(r.get("topic_id", ""), 1.0),
                reverse=True,
            )
    except Exception:
        pass  # Non-critical — proceed with original order

    client = OpenAI(api_key=api_key)

    # Prepare item summary for the prompt (with sanitization)
    research_text = "\n\n".join(
        f"[{i+1}] Title: {_sanitize_text(r.get('title', ''), 200)}\nSource: {_sanitize_text(r.get('source', ''), 50)}\nType: {r.get('type', 'announcement')}\nSummary: {_sanitize_text(r.get('summary', ''), 400)}"
        for i, r in enumerate(research)
    )

    prompt = f"""You are a senior ML engineer reviewing today's AI/dev news.
Rank the following items by relevance to a working ML/AI engineer.
Prioritize:
1. New model releases or major version updates to widely-used tools
2. API changes, new capabilities, or breaking changes that affect production code
3. Significant open-source releases the community will adopt
4. Practical techniques or benchmarks that change how engineers work

Deprioritize:
- Pure academic research with no near-term practical application
- Marketing announcements with no technical substance
- Incremental updates to niche tools

Items:
{research_text}

Return the single most important item as JSON: {{"index": N, "reason": "one sentence why this matters to a dev"}}"""

    try:
        response = _call_openai_ranking(client, prompt)

        content = response.choices[0].message.content
        if content:
            # Try JSON parse first, fall back to plain number
            try:
                result = json.loads(content.strip())
                selected_index = int(result["index"]) - 1
            except (json.JSONDecodeError, KeyError):
                selected_index = int(content.strip()) - 1
            if 0 <= selected_index < len(research):
                return research[selected_index]
    except (ValueError, IndexError, TypeError, AttributeError):
        pass
    except Exception:
        logger.error("Failed to rank items with AI")

    # Fallback to first paper if parsing fails
    return research[0]
