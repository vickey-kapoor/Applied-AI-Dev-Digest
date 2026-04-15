"""Dynamic topic configuration backed by Vercel KV."""

import json
import os
import urllib.parse
import urllib.request

from src.logger import get_logger

logger = get_logger(__name__)

# Mirror of dashboard/src/lib/topics.ts — canonical topic definitions
DEFAULT_TOPICS = [
    {
        "id": "computer_use",
        "keywords": [
            "computer use", "computer-use", "browser use", "browser-use",
            "web agent", "GUI agent", "desktop automation", "UI agent",
            "screen grounding", "screen capture", "operator", "WebArena",
            "playwright", "selenium", "puppeteer", "web automation",
            "click agent", "agentic browser", "web browsing agent",
            "visual agent", "multimodal agent", "SoM", "Set-of-Mark",
            "UI grounding", "web task", "web navigation",
            "computer control", "desktop agent", "GUI automation",
            "OSWorld", "ScreenSpot", "WebVoyager", "Mind2Web",
        ],
        "default_enabled": True,
    },
    {
        "id": "models",
        "keywords": ["GPT", "Claude", "Gemini", "Llama", "Mistral", "model release"],
        "default_enabled": False,
    },
    {
        "id": "apis",
        "keywords": ["API", "SDK", "endpoint", "breaking change", "deprecation"],
        "default_enabled": False,
    },
    {
        "id": "frameworks",
        "keywords": ["LangChain", "LlamaIndex", "AutoGen", "CrewAI", "framework"],
        "default_enabled": False,
    },
    {
        "id": "inference",
        "keywords": ["vLLM", "Ollama", "TensorRT", "quantization", "serving", "deployment"],
        "default_enabled": False,
    },
    {
        "id": "finetuning",
        "keywords": ["fine-tuning", "LoRA", "QLoRA", "Unsloth", "training", "PEFT"],
        "default_enabled": False,
    },
    {
        "id": "rag",
        "keywords": ["RAG", "retrieval", "vector database", "embedding", "memory"],
        "default_enabled": False,
    },
    {
        "id": "agents",
        "keywords": ["agent", "tool use", "multi-agent", "autonomous", "agentic"],
        "default_enabled": False,
    },
    {
        "id": "opensource",
        "keywords": ["open source", "open weights", "Apache", "MIT license"],
        "default_enabled": False,
    },
    {
        "id": "safety",
        "keywords": ["safety", "alignment", "jailbreak", "red-teaming", "guardrails"],
        "default_enabled": False,
    },
    {
        "id": "hardware",
        "keywords": ["GPU", "TPU", "chip", "CUDA", "inference cost", "hardware"],
        "default_enabled": False,
    },
]

# Additional keywords that supplement topic-based filtering
_SUPPLEMENTAL_KEYWORDS = [
    "computer use", "computer-use", "browser use", "browser-use",
    "web agent", "GUI agent", "desktop automation", "UI automation",
    "operator", "WebArena", "OSWorld", "web navigation",
]


def _kv_get(key: str):
    """Fetch a value from Vercel KV REST API. Returns None on any failure."""
    url = os.environ.get("KV_REST_API_URL", "").strip()
    token = os.environ.get("KV_REST_API_TOKEN", "").strip()
    if not url or not token:
        return None

    # Validate URL scheme to prevent SSRF
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        logger.warning("Invalid KV_REST_API_URL scheme or hostname")
        return None

    try:
        req = urllib.request.Request(
            f"{url}/get/{key}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        result = data.get("result")
        if result is None:
            return None
        if isinstance(result, str):
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                return result
        return result
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
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    if not url or not token:
        return {}

    try:
        req = urllib.request.Request(
            f"{url}",
            data=json.dumps(["LRANGE", "feedback:log", "0", "-1"]).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        raw_items = data.get("result", [])
        entries = []
        for raw in raw_items:
            try:
                entry = json.loads(raw) if isinstance(raw, str) else raw
                entries.append(entry)
            except (json.JSONDecodeError, TypeError):
                continue

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
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    if not url or not token:
        return

    try:
        # Read current stats
        stats = _kv_get("stats:topics") or {}
        if not isinstance(stats, dict):
            stats = {}
        stats[topic_id] = stats.get(topic_id, 0) + 1

        # Write back
        data = json.dumps(stats).encode()
        req = urllib.request.Request(
            f"{url}",
            data=json.dumps(["SET", "stats:topics", json.dumps(stats)]).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        logger.info("Incremented topic stat for '%s'", topic_id)
    except Exception as e:
        logger.warning("Could not update topic stats: %s", e)
