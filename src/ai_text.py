"""Shared helpers for preparing research text for LLM prompts."""

import re


def sanitize_prompt_text(text: str, max_length: int = 500) -> str:
    """
    Sanitize text to reduce prompt-injection risk in model inputs.

    - Removes control characters
    - Filters common instruction-overriding patterns
    - Truncates overly long content
    """
    if not text:
        return ""

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    injection_patterns = [
        r"ignore\s+(previous|above|all)\s+instructions?",
        r"disregard\s+(previous|above|all)",
        r"forget\s+(everything|previous|above)",
        r"new\s+instructions?:",
        r"system\s*:",
        r"assistant\s*:",
        r"user\s*:",
        r"\[INST\]",
        r"\[/INST\]",
        r"<\|.*?\|>",
    ]
    for pattern in injection_patterns:
        text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text.strip()
