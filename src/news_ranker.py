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

    prompt = f"""You are a working AI Safety researcher. You read to update your model of how frontier systems behave, how to measure them, and how to align them.
Your job is to pick the single most important item from today's list for an AI Safety researcher.

Rank by epistemic value to a safety researcher.
Prioritize:
1. Empirical findings about model behavior — deception, scheming, sandbagging, alignment faking, situational awareness, reward hacking, with reproducible setups
2. New evaluations or benchmarks measuring dangerous capability, autonomy, persuasion, CBRN uplift, or alignment properties
3. Interpretability results — mechanistic findings, sparse autoencoder discoveries, circuits, activation steering with concrete claims
4. Alignment techniques with measured outcomes — RLHF/RLAIF/DPO/Constitutional AI variants, scalable oversight, debate, weak-to-strong
5. Red-teaming and jailbreak research — novel attacks, robust defenses, automated red-teaming methods
6. Frontier-model system cards / RSPs / preparedness reports with safety-relevant detail
7. Governance actions that materially constrain frontier development (AISIs, EU AI Act enforcement, compute thresholds)
8. Open-weight releases when they shift the safety threat model (fine-tuning attack feasibility, removable safety, capability proliferation)

Deprioritize:
- Capability announcements with no safety eval, system card, or behavioral analysis
- SDK / framework / inference / deployment news
- Pure opinion or position pieces without data, methods, or measurements
- Hiring, partnerships, funding rounds, leadership changes
- Incremental benchmark improvements without methodological insight

Items:
{research_text}

Return the single most important item as JSON: {{"index": N, "reason": "one sentence why this matters to an AI Safety researcher"}}"""

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
