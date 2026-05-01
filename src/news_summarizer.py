"""Generate structured dev-focused summaries for AI/dev news items."""

import json

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.constants import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS_BUNDLE
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


def _prepare_inputs(research: dict) -> tuple[str, str, str]:
    """Sanitize and extract title, source, and summary from an item."""
    title = sanitize_prompt_text(research.get("title", ""), 200)
    source = sanitize_prompt_text(research.get("source", "Unknown"), 100)
    summary = sanitize_prompt_text(research.get("summary", ""), 800)
    return title, source, summary


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(Exception,))
def _call_openai(client: OpenAI, prompt: str) -> str:
    """Make an OpenAI API call with retry logic."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENAI_MAX_TOKENS_BUNDLE,
        temperature=OPENAI_TEMPERATURE,
    )
    return response.choices[0].message.content.strip()


def summarize_research_bundle(research: dict, api_key: str) -> dict:
    """Generate a structured dev-focused summary in a single model call.

    Returns the original item unchanged if the request fails.
    """
    if not api_key:
        return research

    client = OpenAI(api_key=api_key)
    title, source, description = _prepare_inputs(research)

    prompt = f"""You are summarizing for a working AI Safety researcher.
Be direct, empirical, and skeptical. No hype, no marketing language.

Item title: {title}
Source: {source}
Description: {description}

Return JSON (no markdown fences):
{{
  "claim": "One sentence — the central empirical or methodological claim being made",
  "evidence": "2-3 sentences — what specifically supports the claim: experiments run, models tested, sample sizes, key numbers if reported",
  "method": "1-2 sentences — how the work was done: technique used, eval setup, datasets, or analysis pipeline",
  "limitations": "1-2 sentences — honest limitations: scope, model coverage, reproducibility gaps, confounds, or whether claims outrun the evidence",
  "safety_relevance": "One sentence — what this updates about alignment, evaluation, threat models, or governance for frontier systems",
  "rigor": "preprint, peer-reviewed, lab-blog, position, or system-card — tag the source type so the reader weights credibility"
}}"""

    try:
        content = _call_openai(client, prompt)
        # Strip markdown fences if model adds them
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return research

        research_with_summaries = research.copy()

        # Store structured fields
        for key in ("claim", "evidence", "method", "limitations", "safety_relevance", "rigor"):
            if parsed.get(key):
                research_with_summaries[key] = parsed[key]

        # Build short summary for backward compat (Telegram fallback, KV, etc.)
        parts = []
        if parsed.get("claim"):
            parts.append(parsed["claim"])
        if parsed.get("evidence"):
            parts.append(parsed["evidence"])
        if parts:
            research_with_summaries["summary"] = " ".join(parts)

        # Build detailed summary for PDF
        detail_parts = []
        for key, label in [
            ("claim", "Claim"),
            ("evidence", "Evidence"),
            ("method", "Method"),
            ("limitations", "Limitations"),
            ("safety_relevance", "Safety relevance"),
        ]:
            if parsed.get(key):
                detail_parts.append(f"**{label}**\n{parsed[key]}")
        if detail_parts:
            research_with_summaries["detailed_summary"] = "\n\n".join(detail_parts)

        return research_with_summaries
    except Exception:
        logger.warning("Could not generate summaries")
        return research
