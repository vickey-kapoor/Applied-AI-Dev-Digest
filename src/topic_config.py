"""Dynamic topic configuration backed by Vercel KV."""

from src import kv_client
from src.logger import get_logger

logger = get_logger(__name__)

# Mirror of dashboard/src/lib/topics.ts — canonical topic definitions.
# This is the single source of truth for topic ids, display names, and
# keywords on the Python side; json_exporter.extract_topics reads from it
# rather than keeping its own copy.
# Persona: engineer/researcher tracking what the frontier AI labs ship.
# Prioritize model launches, product/API releases, lab research reports, and
# capability results over third-party commentary.
#
# Keywords are matched as case-insensitive substrings against title + summary,
# so short tokens that hide inside common words (e.g. "api" inside "rapid")
# are avoided in favor of multi-word identifiers.
DEFAULT_TOPICS = [
    {
        "id": "model_releases",
        "name": "Model Releases",
        "keywords": [
            "model release", "new model", "frontier model", "flagship model",
            "reasoning model", "model family", "introducing claude",
            "introducing gpt", "GPT-", "Claude", "Gemini", "Llama", "Mistral",
            "Qwen", "DeepSeek", "Grok", "Gemma", "Command R",
        ],
        "default_enabled": True,
    },
    {
        "id": "product_api",
        "name": "Product & API",
        # Only AI-specific terms. The eleven generic ones removed here
        # ("public beta", "SDK", "now available", "general availability",
        # "rolling out", "rate limit", "pricing update", "developer api",
        # "api access", "api pricing", "developer platform") matched any
        # software release anywhere: "public beta" admitted "StreetComplete on
        # iOS is now in public beta", and "SDK" admitted every client-library
        # version bump. This gate now guards only Hacker News and HF Papers,
        # where precision matters far more than breadth.
        "keywords": [
            "batch api", "fine-tuning api", "responses api", "assistants api",
            "context window", "token pricing", "model deprecation",
        ],
        "default_enabled": True,
    },
    {
        "id": "lab_research",
        "name": "Lab Research",
        "keywords": [
            "technical report", "research paper", "scaling law", "pretraining",
            "post-training", "reinforcement learning", "RLHF", "distillation",
            "mixture of experts", "chain of thought", "test-time compute",
            "long context", "sparse attention", "synthetic data",
        ],
        "default_enabled": True,
    },
    {
        "id": "agents_tooling",
        "name": "Agents & Tooling",
        "keywords": [
            "agentic", "AI agent", "tool use", "function calling",
            "computer use", "model context protocol", "MCP server",
            "coding agent", "browser agent", "multi-agent", "tool calling",
            "agent framework",
        ],
        "default_enabled": True,
    },
    {
        "id": "benchmarks",
        "name": "Benchmarks & Evals",
        "keywords": [
            "benchmark", "evaluation suite", "SWE-bench", "GPQA",
            "ARC-AGI", "AIME", "FrontierMath", "MMLU", "leaderboard",
            "state of the art", "human evaluation", "model evaluation",
        ],
        "default_enabled": True,
    },
    {
        "id": "safety_system_cards",
        "name": "Safety & System Cards",
        "keywords": [
            "system card", "model card", "responsible scaling",
            "preparedness framework", "frontier safety", "red-teaming",
            "red teaming", "jailbreak", "prompt injection", "alignment",
            "interpretability", "safety evaluation",
        ],
        "default_enabled": True,
    },
    {
        "id": "open_weights",
        "name": "Open Weights",
        "keywords": [
            "open weights", "open-weight", "open source model", "open model",
            "weights release", "Apache 2.0", "model license",
            "Hugging Face release", "OLMo", "Gemma",
        ],
        "default_enabled": False,
    },
    {
        "id": "infrastructure",
        "name": "Compute & Infrastructure",
        "keywords": [
            "inference", "quantization", "training run", "gpu cluster",
            "TPU", "Blackwell", "Trainium", "supercomputer", "datacenter",
            "serving", "kv cache", "throughput", "compute deal",
        ],
        "default_enabled": False,
    },
    {
        "id": "multimodal",
        "name": "Multimodal & Generative Media",
        "keywords": [
            "multimodal", "vision-language", "image generation",
            "video generation", "text-to-video", "speech model", "voice model",
            "text-to-speech", "world model", "diffusion model", "audio model",
        ],
        "default_enabled": False,
    },
    {
        "id": "enterprise_deployment",
        "name": "Enterprise Deployment",
        "keywords": [
            "enterprise", "deployment", "case study", "on-premise",
            "government deployment", "cloud partnership", "customer adoption",
            "production deployment", "compliance certification",
        ],
        "default_enabled": False,
    },
    {
        "id": "policy_regulation",
        "name": "Policy & Regulation",
        "keywords": [
            "EU AI Act", "AI regulation", "AI policy", "executive order",
            "AI safety institute", "AISI", "export controls",
            "compute governance", "AI legislation",
        ],
        "default_enabled": False,
    },
]

# Additional keywords that supplement topic-based filtering
_SUPPLEMENTAL_KEYWORDS = [
    # Keep empty — the topic keyword sets above are already high-precision.
]


def _kv_get(key: str):
    """Fetch a value from KV, returning None on any failure.

    Topic configuration must never be able to stop a digest: every caller here
    falls back to the built-in defaults when this returns None, so a KV outage
    degrades the digest rather than failing it. kv_client raises by design, so
    this is the boundary where that is converted into a None.
    """
    if not kv_client.kv_configured():
        return None
    try:
        return kv_client.kv_get(key)
    except Exception as e:
        logger.warning("Could not read KV key '%s': %s", key, e)
        return None


def _fetch_kv_config() -> dict | None:
    """Fetch topic config from Vercel KV REST API."""
    return _kv_get("topics:config")


def _get_enabled_topics(kv_config: dict | None) -> list[dict]:
    """Return topics that are enabled based on KV config or defaults."""
    enabled = []
    for topic in DEFAULT_TOPICS:
        if kv_config is not None:
            is_on = kv_config.get(topic["id"], topic["default_enabled"])
        else:
            is_on = topic["default_enabled"]
        if is_on:
            enabled.append(topic)
    return enabled


def get_active_topics() -> list[dict]:
    """Get the list of currently enabled topics."""
    kv_config = _fetch_kv_config()
    return _get_enabled_topics(kv_config)


def get_active_keywords() -> list[str]:
    """Get deduplicated keywords from all active topics, custom keywords, and supplementals."""
    topics = get_active_topics()
    keywords = set()
    for topic in topics:
        keywords.update(topic["keywords"])
    keywords.update(_SUPPLEMENTAL_KEYWORDS)

    # Merge custom keywords from KV
    custom = _kv_get("topics:custom_keywords")
    if isinstance(custom, dict):
        active_ids = {t["id"] for t in topics}
        for topic_id, kw_list in custom.items():
            if topic_id in active_ids and isinstance(kw_list, list):
                keywords.update(kw for kw in kw_list if isinstance(kw, str))

    return sorted(keywords)


def is_paused() -> bool:
    """Check if the digest is paused via KV."""
    result = _kv_get("digest:paused")
    return result is True or result == "true"


def get_feedback_weights() -> dict[str, float]:
    """Get per-topic score multipliers based on user feedback.

    Reads feedback:log from KV, filters to last 30 days, and computes:
      multiplier = 1.0 + (thumbs_up - thumbs_down) * 0.05
      clamped to [0.75, 1.25]
    Returns a dict of {topic_id: multiplier}.
    """
    if not kv_client.kv_configured():
        return {}

    try:
        # kv_get_list already parses each entry and drops unparseable ones.
        entries = kv_client.kv_get_list("feedback:log")

        # Filter to last 30 days
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        recent = [e for e in entries if e.get("date", "") >= cutoff]

        # Tally per topic
        tally: dict[str, int] = {}
        for entry in recent:
            tid = entry.get("topic_id", "")
            if not tid:
                continue
            rating = entry.get("rating", 0)
            tally[tid] = tally.get(tid, 0) + rating

        # Compute clamped multipliers
        weights: dict[str, float] = {}
        for tid, net in tally.items():
            multiplier = 1.0 + net * 0.05
            weights[tid] = max(0.75, min(1.25, multiplier))

        return weights
    except Exception as e:
        logger.warning("Could not read feedback log from KV: %s", e)
        return {}


def increment_topic_stat(topic_id: str) -> None:
    """Increment the win counter for a topic in KV stats."""
    if not kv_client.kv_configured():
        return

    try:
        stats = _kv_get("stats:topics") or {}
        if not isinstance(stats, dict):
            stats = {}
        stats[topic_id] = stats.get(topic_id, 0) + 1
        kv_client.kv_set("stats:topics", stats)
        logger.info("Incremented topic stat for '%s'", topic_id)
    except Exception as e:
        logger.warning("Could not update topic stats: %s", e)
