"""Generate structured lab-release briefs for AI lab developments."""

import json

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.constants import OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS_BUNDLE
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


# The feed blurb is a teaser; the article is the real input. Generous but
# bounded, so one long post cannot dominate the prompt.
ARTICLE_CHAR_BUDGET = 8000
SUMMARY_CHAR_BUDGET = 800


# How the body text is introduced to the model. Which one is used is itself
# information: a model told it is reading a teaser abstains where a model told
# it is reading the article guesses.
FULL_TEXT_LABEL = "Article text"
TEASER_LABEL = "Feed teaser only — the full post could not be retrieved, so this is all there is"


def _prepare_inputs(item: dict) -> tuple[str, str, str, str]:
    """Sanitize title, source, the best available body text, and its label.

    Prefers article_text, which main.py fills by opening the link and which
    some fetchers supply directly. Feed summaries ran a median of 273
    characters and were sometimes empty — the DeepMind post announcing Gemini 4
    Argon carried none at all — so five structured fields were being written
    from a title and two sentences, and `availability` came back a non-answer
    39% of the time. Falls back to the feed summary when the page could not be
    read, and says so in the label: OpenAI's posts are behind a bot challenge
    that returns 403 whatever headers we send, so those items will keep
    arriving as ~150 characters and the model should not dress that up.
    """
    title = sanitize_prompt_text(item.get("title", ""), 200)
    source = sanitize_prompt_text(item.get("source", "Unknown"), 100)

    article = (item.get("article_text") or "").strip()
    if article:
        return title, source, sanitize_prompt_text(article, ARTICLE_CHAR_BUDGET), FULL_TEXT_LABEL
    return (
        title,
        source,
        sanitize_prompt_text(item.get("summary", ""), SUMMARY_CHAR_BUDGET),
        TEASER_LABEL,
    )


@retry_with_backoff(exceptions=(Exception,))
def _call_openai(client: OpenAI, prompt: str) -> str:
    """Make an OpenAI API call with retry logic."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENAI_MAX_TOKENS_BUNDLE,
        temperature=OPENAI_TEMPERATURE,
    )
    return response.choices[0].message.content.strip()


# Structured fields produced by the model, in the order they read best.
SUMMARY_FIELDS = (
    "what_shipped",
    "capabilities",
    "availability",
    "why_it_matters",
    "caveats",
    "release_type",
)

# Fields rendered into the long-form PDF body, with their display labels.
DETAIL_SECTIONS = (
    ("what_shipped", "What shipped"),
    ("capabilities", "Capabilities"),
    ("availability", "Availability"),
    ("why_it_matters", "Why it matters"),
    ("caveats", "Caveats"),
)


def summarize_release(item: dict, api_key: str) -> dict:
    """Generate a structured lab-release brief in a single model call.

    Returns the original item unchanged if the request fails.
    """
    if not api_key:
        return item

    client = OpenAI(api_key=api_key)
    title, source, description, body_label = _prepare_inputs(item)

    prompt = f"""You are briefing an applied AI engineer: someone who builds production systems on models — serving them, evaluating them, wiring them into agents and products. Write for what they have to decide, not for what is notable about the field.
Be concrete and factual. No hype, no marketing language. Prefer specifics — model names, numbers, prices, dates — over adjectives.
If the text below does not state something, say so rather than inventing it. A thin teaser is not licence to guess — write "Not stated" and let the reader click through.

Item title: {title}
Source: {source}
{body_label}: {description}

Return JSON (no markdown fences):
{{
  "what_shipped": "One sentence — which lab shipped what: the model, product, API, paper, or result, named precisely",
  "capabilities": "2-3 sentences — what it can do that matters: modalities, context length, benchmark numbers, speed or quality claims, with the figures given",
  "availability": "1-2 sentences — how to get it today: API, app, open weights, waitlist, preview or GA, regions, pricing and tiers if stated. This is often the field that decides whether the reader can act, so be specific. Say 'not stated' if the description does not say",
  "why_it_matters": "1-2 sentences — what this changes for someone building on models: a capability they can now use, a cost or latency tradeoff that moved, a technique worth adopting, or a reason to revisit a choice they already made. Concrete consequence for their own stack, not significance to the industry",
  "caveats": "1-2 sentences — the honest limits: unverified claims, benchmark caveats, limited access, missing detail, or where the announcement outruns the evidence",
  "release_type": "model, product, api, research, open-weights, infrastructure, safety, or policy — tag what kind of development this is"
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
            return item

        enriched = item.copy()

        # Store structured fields
        for key in SUMMARY_FIELDS:
            if parsed.get(key):
                enriched[key] = parsed[key]

        # Build short summary for backward compat (Telegram fallback, KV, etc.)
        parts = []
        if parsed.get("what_shipped"):
            parts.append(parsed["what_shipped"])
        if parsed.get("capabilities"):
            parts.append(parsed["capabilities"])
        if parts:
            enriched["summary"] = " ".join(parts)

        # Build detailed summary for PDF
        detail_parts = []
        for key, label in DETAIL_SECTIONS:
            if parsed.get(key):
                detail_parts.append(f"**{label}**\n{parsed[key]}")
        if detail_parts:
            enriched["detailed_summary"] = "\n\n".join(detail_parts)

        return enriched
    except Exception:
        logger.warning("Could not generate summaries")
        return item
