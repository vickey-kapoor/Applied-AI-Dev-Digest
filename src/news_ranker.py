"""Rank AI product updates by developer usefulness using OpenAI."""

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.logger import get_logger

logger = get_logger(__name__)
_sanitize_text = sanitize_prompt_text


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

Product Updates:
{research_text}

Respond with ONLY the number (e.g., "1" or "3"). No explanation."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0,
        )

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
