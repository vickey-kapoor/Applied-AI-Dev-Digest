"""Generate structured lab-release briefs for AI lab developments."""

import json

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.constants import (
    OPENAI_MODEL_SUMMARY,
    OPENAI_TEMPERATURE,
    OPENAI_MAX_TOKENS_BUNDLE,
    OPENAI_REASONING_EFFORT,
)
from src.logger import get_logger
from src.openai_call import call_json, json_schema_format, reply_text
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


# Structured fields produced by the model, in the order they read best.
SUMMARY_FIELDS = (
    "what_shipped",
    "capabilities",
    "availability",
    "why_it_matters",
    "caveats",
    "release_type",
)

RELEASE_TYPES = (
    "model",
    "product",
    "api",
    "research",
    "open-weights",
    "infrastructure",
    "safety",
    "policy",
)

# The brief's shape, enforced by the API rather than asked for in prose.
#
# This call asked for JSON in the prompt and sent no response_format at all,
# so the reply arrived fenced often enough that the parser below strips fences
# by hand. Worse, a reply that did not parse was swallowed: summarize_release
# returns the item unchanged, main.py logs "Could not generate summaries", and
# the digest goes out with the raw feed blurb in place of the five fields —
# the same silent degradation the ranker had. The schema makes the five fields
# and the release_type vocabulary the API's problem.
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        **{field: {"type": "string"} for field in SUMMARY_FIELDS if field != "release_type"},
        "release_type": {"type": "string", "enum": list(RELEASE_TYPES)},
    },
    "required": list(SUMMARY_FIELDS),
    "additionalProperties": False,
}


@retry_with_backoff(exceptions=(Exception,))
def _call_openai(client: OpenAI, prompt: str) -> str:
    """Make an OpenAI API call with retry logic."""
    response = call_json(
        client,
        model=OPENAI_MODEL_SUMMARY,
        prompt=prompt,
        max_output_tokens=OPENAI_MAX_TOKENS_BUNDLE,
        response_format=json_schema_format("release_brief", SUMMARY_SCHEMA),
        temperature=OPENAI_TEMPERATURE,
        reasoning_effort=OPENAI_REASONING_EFFORT,
    )
    content, finish_reason = reply_text(response)
    if not content:
        # Same empty-reply shape the ranker guards against. Here the cost is
        # the brief, and the caller's handler says only "Could not generate
        # summaries", so the reason has to be logged where it is known.
        logger.warning("Empty summary reply (finish_reason=%s)", finish_reason)
    return content


# Fields rendered into the long-form brief, with their display labels.
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

        # Build the long-form brief
        detail_parts = []
        for key, label in DETAIL_SECTIONS:
            if parsed.get(key):
                detail_parts.append(f"**{label}**\n{parsed[key]}")
        if detail_parts:
            enriched["detailed_summary"] = "\n\n".join(detail_parts)

        return enriched
    except Exception as e:
        # With the reason: this handler covers the API call, the JSON parse and
        # the field extraction alike, and "Could not generate summaries" told
        # the three apart not at all. The digest still ships, on the feed blurb.
        logger.warning("Could not generate summaries: %s: %s", type(e).__name__, e)
        return item
