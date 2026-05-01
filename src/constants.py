"""Centralized constants for AI Dev Digest."""

import os

# Application info
APP_NAME = "AI Dev Digest"
APP_VERSION = "2.0.0"
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (https://github.com/vickey-kapoor/ai-research-digest)"

# Network settings
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3

# Deduplication settings
DEDUP_SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.85"))

# Digest settings
DIGEST_MAX_RESULTS = int(os.getenv("DIGEST_MAX_RESULTS", "10"))

# OpenAI model settings
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS_RANKING = 150
OPENAI_MAX_TOKENS_SUMMARY = 500
OPENAI_MAX_TOKENS_DETAILED = 1500
OPENAI_MAX_TOKENS_BUNDLE = 1800

# Telegram settings
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Data cap settings
PAPERS_CAP = 500
DIGEST_CAP_DAYS = 90

# Thread pool settings
THREAD_POOL_WORKERS = 2

# Persona: AI Safety researcher.
# Default keyword set — broad safety vocabulary used as a fallback when no
# topic-config keywords are passed through. Topic-level filtering (in
# topic_config.DEFAULT_TOPICS) is the primary signal.
FILTER_KEYWORDS = [
    # Alignment
    "alignment", "rlhf", "rlaif", "dpo", "constitutional ai",
    "scalable oversight", "weak-to-strong", "reward model", "reward hacking",
    # Interpretability
    "interpretability", "mechanistic", "sparse autoencoder", "sae",
    "activation steering", "probing", "monosemanticity", "transformerlens",
    # Evals
    "benchmark", "eval", "capability eval", "dangerous capability",
    "autonomy eval", "inspect_ai", "metr",
    # Red-teaming
    "red-teaming", "red teaming", "jailbreak", "prompt injection",
    "adversarial prompt", "garak",
    # System cards / RSP
    "system card", "model card", "responsible scaling", "rsp",
    "preparedness framework", "frontier safety",
    # Agentic safety
    "deception", "scheming", "sandbagging", "situational awareness",
    "alignment faking", "sabotage",
    # Governance
    "ai safety institute", "aisi", "eu ai act", "compute governance",
    # Catastrophic risk
    "cbrn", "biorisk", "cyber uplift", "wmdp",
    # Robustness / data
    "adversarial robustness", "distribution shift", "data poisoning",
    "watermarking", "memorization",
]

# Keywords to exclude non-research content (lowercase)
EXCLUDE_KEYWORDS = [
    "partnership",
    "partners with",
    "hiring",
    "careers",
    "joins",
    "leadership",
    "appointed",
    "raises",
    "funding round",
    "series a",
    "series b",
    "ipo",
]

# Blog RSS feeds — AI Safety research orgs
BLOG_FEEDS = {
    "Anthropic": "https://www.anthropic.com/news/rss.xml",
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Apollo Research": "https://www.apolloresearch.ai/blog/rss.xml",
    "METR": "https://metr.org/blog/feed.xml",
    "Redwood Research": "https://redwoodresearch.substack.com/feed",
    "AI Alignment Forum": "https://www.alignmentforum.org/feed.xml",
    "Center for AI Safety": "https://safe.ai/blog/rss.xml",
}

# GitHub repos disabled in Phase 1 — none of the prior dev-toolchain repos
# are safety-relevant. Phase 2 will enable a focused list (TransformerLens,
# sae_lens, inspect_ai, garak, etc.).
GITHUB_REPOS: list[str] = []

# Hacker News filter keywords — AI Safety topics
HN_KEYWORDS = [
    # Alignment / interp
    "alignment", "rlhf", "constitutional ai", "interpretability",
    "mechanistic interpretability", "sparse autoencoder",
    # Evals / red-teaming
    "evaluation", "benchmark", "jailbreak", "red-teaming", "prompt injection",
    "dangerous capability",
    # Model cards / RSP
    "system card", "model card", "responsible scaling", "frontier safety",
    "preparedness framework",
    # Agentic safety
    "scheming", "deception", "alignment faking", "sandbagging",
    "situational awareness",
    # Governance
    "AI safety institute", "AISI", "EU AI Act",
    # Catastrophic risk
    "biorisk", "CBRN", "WMDP",
]
HN_MIN_SCORE = 100
HN_MAX_STORIES = 5

# Hugging Face Daily Papers — bumped to 25+ for Phase 1 to favor signal.
# Safety papers are rarely viral; if this is too restrictive in practice,
# tune downward after a week of observation.
HF_MIN_UPVOTES = 25
HF_MAX_PAPERS = 5
