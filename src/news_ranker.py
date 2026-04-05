"""Rank AI product updates by developer usefulness using OpenAI."""

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

    # Prepare update summary for the prompt (with sanitization)
    research_text = "\n\n".join(
        f"[{i+1}] Title: {_sanitize_text(r.get('title', ''), 200)}\nLab: {_sanitize_text(r.get('source', ''), 50)}\nDescription: {_sanitize_text(r.get('description', ''), 400)}"
        for i, r in enumerate(research)
    )

    prompt = f"""You are a developer tools curator tracking AI lab product announcements.

Select the ONE most important update that a software developer should know about today.

Consider:
1. Can a developer try this RIGHT NOW? (new API, SDK, model, tool)
2. How significant is the new capability? (new model > minor update)
3. Breadth of developer impact (affects many developers vs. niche use case)
4. Novelty (first-of-its-kind vs. incremental improvement)
5. SKIP corporate announcements (partnerships, policy, hiring, leadership, funding) — only pick developer-facing product updates.

Product Updates:
{research_text}

Respond with ONLY the number (e.g., "1" or "3"). No explanation."""

    try:
        response = _call_openai_ranking(client, prompt)

        content = response.choices[0].message.content
        if content:
            selected_index = int(content.strip()) - 1
            if 0 <= selected_index < len(research):
                return research[selected_index]
    except (ValueError, IndexError, TypeError, AttributeError):
        pass
    except Exception:
        logger.error("Failed to rank research with AI")

    # Fallback to first paper if parsing fails
    return research[0]
