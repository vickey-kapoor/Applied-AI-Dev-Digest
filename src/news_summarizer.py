"""Generate developer-focused summaries for AI product updates."""

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.logger import get_logger

logger = get_logger(__name__)
_sanitize_text = sanitize_prompt_text

def summarize_research(research: dict, api_key: str) -> dict:
    """
    Generate a concise developer-focused summary for a product update.

    Args:
        research: Product update dictionary with title, description, source, url
        api_key: OpenAI API key

    Returns:
        Update dictionary with added 'summary' field
    """
    if not api_key:
        return research

    client = OpenAI(api_key=api_key)

    # Sanitize inputs to prevent prompt injection
    title = _sanitize_text(research.get("title", ""), 200)
    lab = _sanitize_text(research.get("source", "Unknown"), 100)
    description = _sanitize_text(research.get("description", ""), 500)

    prompt = f"""You summarize AI product announcements for busy developers.

Update: {title}
From: {lab}
Details: {description}

Write 3-4 concise sentences covering:
1. What was launched or updated?
2. What can developers do with this that they couldn't before?
3. How to get started (API key, SDK install, pricing tier if known)?

RULES:
- Be concise and practical
- Include specific technical details (model names, API endpoints, pricing)
- Focus on "what can I try today"
- No hype, no marketing speak

Now write the summary:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )

        summary = response.choices[0].message.content.strip()
        research_with_summary = research.copy()
        research_with_summary["summary"] = summary
        return research_with_summary

    except Exception:
        logger.warning("Could not generate summary")
        return research


def summarize_research_detailed(research: dict, api_key: str) -> dict:
    """
    Generate a detailed developer-focused summary for PDF reports.

    Args:
        research: Product update dictionary with title, description, source, url
        api_key: OpenAI API key

    Returns:
        Update dictionary with added 'detailed_summary' field
    """
    if not api_key:
        return research

    client = OpenAI(api_key=api_key)

    # Sanitize inputs
    title = _sanitize_text(research.get("title", ""), 200)
    lab = _sanitize_text(research.get("source", "Unknown"), 100)
    description = _sanitize_text(research.get("description", ""), 800)

    prompt = f"""You are a technical writer creating an in-depth developer briefing on an AI product update.

Update: {title}
From: {lab}
Details: {description}

Write a DETAILED explanation (6-10 paragraphs) covering:

1. **What Was Announced** (1-2 paragraphs)
   - What is the product, feature, or model?
   - What problem does it solve for developers?

2. **Technical Capabilities** (2-3 paragraphs)
   - Key technical specs (context window, speed, pricing, limits)
   - What APIs or SDKs are available?
   - What can you build with this?

3. **Getting Started** (1-2 paragraphs)
   - How to access it (sign up, API key, install SDK)
   - Quick example of how to use it

4. **How It Compares** (1-2 paragraphs)
   - How does this compare to alternatives from other labs?
   - What's unique about this offering?

5. **Bottom Line for Developers** (1 paragraph)
   - Is this worth trying today?
   - Who benefits most?

RULES:
- Be technical but clear
- Include concrete details (model names, pricing, endpoints)
- Focus on practical developer value
- No marketing fluff

Now write the detailed explanation:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7,
        )

        detailed_summary = response.choices[0].message.content.strip()
        research_with_summary = research.copy()
        research_with_summary["detailed_summary"] = detailed_summary
        return research_with_summary

    except Exception:
        logger.warning("Could not generate detailed summary")
        return research


def summarize_research_bundle(research: dict, api_key: str) -> dict:
    """
    Generate both short and detailed summaries in a single model call.

    Returns the original paper unchanged if the request fails.
    """
    if not api_key:
        return research

    client = OpenAI(api_key=api_key)

    title = sanitize_prompt_text(research.get("title", ""), 200)
    authors = sanitize_prompt_text(research.get("authors", "Unknown"), 100)
    abstract = sanitize_prompt_text(research.get("description", ""), 800)

    prompt = f"""You explain AI research to people with no technical background.

Paper: {title}
Authors: {authors}
Abstract: {abstract}

Write two outputs:

SHORT_SUMMARY:
- 4-5 simple sentences
- explain the problem, what they built, how it works in everyday terms, and why a regular person should care

DETAILED_SUMMARY:
- 8-12 paragraphs
- explain the big picture, what they did, why it is clever, real-world impact, and the bottom line

RULES:
- No jargon
- No technical terms like model, algorithm, neural network, training, parameters, architecture, benchmark, transformer, LLM
- Use everyday analogies
- Be warm and conversational

Respond in exactly this format:
SHORT_SUMMARY:
<text>

DETAILED_SUMMARY:
<text>"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1800,
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        parts = content.split("DETAILED_SUMMARY:", maxsplit=1)
        if len(parts) != 2 or "SHORT_SUMMARY:" not in parts[0]:
            return research

        short_summary = parts[0].split("SHORT_SUMMARY:", maxsplit=1)[1].strip()
        detailed_summary = parts[1].strip()
        if not short_summary and not detailed_summary:
            return research

        research_with_summaries = research.copy()
        if short_summary:
            research_with_summaries["summary"] = short_summary
        if detailed_summary:
            research_with_summaries["detailed_summary"] = detailed_summary
        return research_with_summaries
    except Exception:
        logger.warning("Could not generate summaries")
        return research
