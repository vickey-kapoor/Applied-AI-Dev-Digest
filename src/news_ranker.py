"""Rank AI/dev news by relevance to computer use agent developers using OpenAI."""

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
    Use OpenAI to select the most important computer use agent update for developers.

    Args:
        research: List of product update dictionaries
        api_key: OpenAI API key

    Returns:
        The most important computer use agent update
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

    prompt = f"""You are a senior Applied AI Engineer — you build production AI systems using LLMs, agents, RAG pipelines, and fine-tuned models.
Your job is to pick the single most important update from today's items for engineers building AI-powered products.

Rank the following items by practical value to an Applied AI Engineer.
Prioritize:
1. New model releases or major capability upgrades (GPT, Claude, Gemini, Llama, Mistral) that change what you can build
2. SDK or API changes (OpenAI, Anthropic, Hugging Face) that directly affect production code
3. New frameworks or libraries that meaningfully improve how AI apps are built (LangChain, LlamaIndex, vLLM, LiteLLM)
4. RAG, retrieval, or embedding improvements with real performance gains
5. Fine-tuning tools or techniques that are practical on consumer/cloud hardware (LoRA, Unsloth, QLoRA)
6. Agent and multi-agent frameworks with working code and demos
7. Computer use / browser / GUI agent releases that push automation capabilities
8. Inference and deployment improvements that reduce cost or latency in production

Deprioritize:
- Pure academic research with no code, API, or near-term practical application
- Marketing announcements with no technical substance
- Incremental patch releases with only bug fixes
- Business/partnership news with no developer impact

Items:
{research_text}

Return the single most important item as JSON: {{"index": N, "reason": "one sentence why this matters to an Applied AI Engineer"}}"""

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
