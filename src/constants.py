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

# Keywords for developer-facing product features
PRODUCT_FEATURE_KEYWORDS = [
    "API",
    "SDK",
    "model release",
    "new feature",
    "changelog",
    "launch",
    "developer tools",
    "fine-tuning",
    "embeddings",
    "function calling",
    "tool use",
    "multimodal",
    "context window",
    "CLI",
    "pricing",
    "general availability",
    "beta",
]

# Simplified keywords for filtering (lowercase)
FILTER_KEYWORDS = [
    "api",
    "sdk",
    "model",
    "release",
    "launch",
    "new",
    "developer",
    "fine-tuning",
    "fine-tune",
    "embeddings",
    "function calling",
    "tool use",
    "multimodal",
    "context window",
    "cli",
    "pricing",
    "generally available",
    "beta",
    "endpoint",
    "playground",
    "library",
    "integration",
]

# Blog RSS feeds for Tier 1 AI Labs
BLOG_FEEDS = {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Anthropic": "https://www.anthropic.com/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Meta AI": "https://ai.meta.com/blog/rss/",
}
