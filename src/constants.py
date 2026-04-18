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

# Keywords for developer-facing computer use agent features
PRODUCT_FEATURE_KEYWORDS = [
    "computer use",
    "computer-use",
    "browser use",
    "browser-use",
    "WebArena",
    "webarena",
    "OSWorld",
    "osworld",
    "ScreenSpot",
    "screenspot",
    "WebVoyager",
    "webvoyager",
    "Mind2Web",
    "mind2web",
    "playwright",
    "puppeteer",
    "selenium",
    "click agent",
    "agentic browser",
    "screen grounding",
    "screen capture",
    "computer control",
    "GUI automation",
    "GUI agent",
    "web automation",
    "web browsing agent",
    "desktop agent",
]

# Simplified keywords for filtering (lowercase) — computer use agents only
FILTER_KEYWORDS = [
    "computer use",
    "computer-use",
    "browser use",
    "browser-use",
    "webarena",
    "osworld",
    "screenspot",
    "webvoyager",
    "mind2web",
    "playwright",
    "puppeteer",
    "selenium",
    "click agent",
    "agentic browser",
    "screen grounding",
    "screen capture",
    "computer control",
    "gui automation",
    "gui agent",
    "web automation",
    "web browsing agent",
    "desktop agent",
]

# Keywords to exclude non-developer content (lowercase)
EXCLUDE_KEYWORDS = [
    "partnership",
    "partners with",
    "policy",
    "regulation",
    "safety board",
    "advisory",
    "hiring",
    "careers",
    "joins",
    "leadership",
    "appointed",
    "raises",
    "funding round",
]

# Blog RSS feeds for AI labs and platforms
BLOG_FEEDS = {
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Meta AI": "https://engineering.fb.com/category/ml-applications/feed/",
    "Microsoft AI": "https://blogs.microsoft.com/ai/feed/",
    "AWS AI": "https://aws.amazon.com/blogs/machine-learning/feed/",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "PyTorch": "https://pytorch.org/blog/feed.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
}

# GitHub repos to track for releases — Applied AI Engineer toolchain
GITHUB_REPOS = [
    "openai/openai-python",
    "anthropics/anthropic-sdk-python",
    "langchain-ai/langchain",
    "BerriAI/litellm",
    "vllm-project/vllm",
    "ggerganov/llama.cpp",
    "microsoft/playwright-python",
    "browser-use/browser-use",
    "run-llama/llama_index",
    "unslothai/unsloth",
]

# Hacker News filter keywords — Applied AI Engineer topics
HN_KEYWORDS = [
    # Models & APIs
    "openai api", "anthropic api", "claude api", "gemini api",
    "model release", "fine-tuning", "LoRA", "QLoRA",
    # Frameworks & tools
    "langchain", "llamaindex", "autogen", "crewai", "litellm",
    "vllm", "ollama", "llama.cpp", "unsloth",
    # Patterns
    "RAG", "retrieval augmented", "vector database", "embeddings",
    "function calling", "tool use", "multi-agent",
    # Computer use / agents
    "computer use", "browser use", "gui agent", "web agent",
    "playwright", "autonomous agent", "agentic",
    # Deployment
    "quantization", "inference server", "model serving",
]
HN_MIN_SCORE = 100
HN_MAX_STORIES = 5

# Hugging Face Daily Papers settings
HF_MIN_UPVOTES = 10
HF_MAX_PAPERS = 5
