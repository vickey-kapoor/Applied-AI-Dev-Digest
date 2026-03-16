"""Generate developer-focused summaries for AI product updates."""

import re

from openai import OpenAI

from src.logger import get_logger

logger = get_logger(__name__)


def _sanitize_text(text: str, max_length: int = 500) -> str:
    """
    Sanitize text to prevent prompt injection.

    - Removes potential injection patterns
    - Limits length
    - Strips control characters
    """
    if not text:
        return ""

    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Remove potential prompt injection patterns
    injection_patterns = [
        r'ignore\s+(previous|above|all)\s+instructions?',
        r'disregard\s+(previous|above|all)',
        r'forget\s+(everything|previous|above)',
        r'new\s+instructions?:',
        r'system\s*:',
        r'assistant\s*:',
        r'user\s*:',
        r'\[INST\]',
        r'\[/INST\]',
        r'<\|.*?\|>',
    ]
    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text.strip()


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
