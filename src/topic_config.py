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
# are avoided in favor of multi-word identifiers. Two measured casualties of
# that rule were "serving", 3 of whose 4 matches were the word *preserving*,
# and "jailbreak", which admitted a Nintendo Switch jailbreak from Hacker
# News; both are gone.
#
# Every keyword here has matched at least one real item in the 500-item pool
# in data/papers.json. The 28-Oct-2026 topics audit removed 36 that had never
# matched anything in 15 months, and repaired four that were dead only because
# of spelling: "open weights" -> "open-weight", "long context" ->
# "long-context", "mixture of experts" -> "mixture-of-experts", and
# "model deprecation" -> "deprecat", which catches deprecated/deprecation
# alike. The audit report is source-audit/2026-10-28-topics-audit.md in the
# project files.
#
# `weak_keywords` are keywords that gate but barely tag — see TOPIC_* weights
# and _topic_match below. They exist because bare model-family names ("Claude",
# "GPT-") are what admit a Hacker News story in the first place, and were also
# deciding its topic: 98 of model_releases' 116 matches over 60 days came from
# a brand name alone with no release language anywhere, so an agent-harness
# post or an SDK bump was filed as a model release. The names still open the
# gate; they no longer outvote a topic that matched on substance.
DEFAULT_TOPICS = [
    {
        "id": "model_releases",
        "name": "Model Releases",
        "keywords": [
            "new model", "frontier model", "reasoning model", "model family",
            "introducing gpt",
        ],
        # Brand names: the gate's workhorses, and deliberately weak at tagging.
        # "Command R" is gone — no match in 500 items.
        "weak_keywords": [
            "GPT-", "Claude", "Gemini", "Llama", "Mistral", "Qwen",
            "DeepSeek", "Grok", "Gemma",
        ],
        "default_enabled": True,
    },
    {
        "id": "product_api",
        "name": "Product & API",
        # Only AI-specific terms. The eleven generic ones removed earlier
        # ("public beta", "SDK", "now available", "general availability",
        # "rolling out", "rate limit", "pricing update", "developer api",
        # "api access", "api pricing", "developer platform") matched any
        # software release anywhere: "public beta" admitted "StreetComplete on
        # iOS is now in public beta", and "SDK" admitted every client-library
        # version bump. This gate now guards only Hacker News and HF Papers,
        # where precision matters far more than breadth.
        "keywords": [
            "responses api", "context window", "context length", "deprecat",
        ],
        "default_enabled": True,
    },
    {
        "id": "lab_research",
        "name": "Lab Research",
        "keywords": [
            "technical report", "scaling law", "pretraining", "post-training",
            "reinforcement learning", "RLHF", "distillation",
            "mixture-of-experts", "long-context", "synthetic data",
        ],
        "default_enabled": True,
    },
    {
        "id": "agents_tooling",
        "name": "Agents & Tooling",
        "keywords": [
            "agentic", "AI agent", "tool use", "tool calling",
            "tool definition", "computer use", "model context protocol",
            "agent skills", "coding agent", "browser agent", "multi-agent",
            "agent framework",
        ],
        "default_enabled": True,
    },
    {
        "id": "benchmarks",
        "name": "Benchmarks & Evals",
        "keywords": [
            "benchmark", "leaderboard", "SWE-bench", "ARC-AGI", "AIME",
            "model evaluation",
        ],
        "default_enabled": True,
    },
    {
        "id": "safety_system_cards",
        "name": "Safety & System Cards",
        # Re-pointed at the vocabulary the labs actually publish under. The
        # five terms this topic was built on ("model card", "responsible
        # scaling", "frontier safety", "safety evaluation" and the since-
        # dropped "jailbreak") never caught a lab safety post; "system card"
        # did, three times, so it stays.
        "keywords": [
            "system card", "safety case", "misalignment", "reward hacking",
            "eval awareness", "preparedness framework", "red-teaming",
            "red teaming", "prompt injection", "alignment",
            "interpretability",
        ],
        "default_enabled": True,
    },
    {
        "id": "open_weights",
        "name": "Open Weights",
        # "Gemma" lived here and in model_releases, and first-match tagging
        # meant this topic never once received it. It is now a model_releases
        # brand name only; an open-weights Gemma post reaches this topic on
        # "open-weight" or "open model", which outscores a brand name.
        "keywords": [
            "open-weight", "open model", "open source model",
            "Hugging Face release", "OLMo",
        ],
        "default_enabled": True,
    },
    {
        "id": "infrastructure",
        "name": "Compute & Infrastructure",
        "keywords": [
            "inference", "quantiz", "gpu cluster", "TPU", "Blackwell",
            "Trainium", "supercomputer", "kv cache",
        ],
        "default_enabled": True,
    },
    {
        "id": "multimodal",
        "name": "Multimodal & Generative Media",
        # On by default as of the 28-Oct-2026 audit. While it was off it
        # contributed no keywords to the gate at all, so a video or speech
        # model launch was dropped outright from Hacker News and HF Papers,
        # and arrived from a lab's own blog with no topic — DeepMind's
        # "Genie 4" sat in the pool untagged.
        "keywords": [
            "multimodal", "vision-language", "image generation",
            "video generation", "video model", "text-to-speech",
            "speech-to-text", "diffusion model", "world model",
            "world simulation",
        ],
        # The exception to the measured-keywords rule, and the reason the rule
        # is worth stating: these are generative-media model families with no
        # other route through the gate. "Genie" has two matches, one of them
        # the alignment idiom "literal genie"; "Sora" has none yet. Both are
        # weak, so neither can decide a topic on its own.
        "weak_keywords": ["Sora", "Genie"],
        "default_enabled": True,
    },
]

# Topics retired by the 28-Oct-2026 audit, kept here as a record so a stats
# page or KV entry naming one is recognisable rather than mysterious:
#   enterprise_deployment — 4 matches in 60 days, three of them NVIDIA
#     consumer posts caught by "deployment" ("'Call of Duty: Modern Warfare 4'
#     Arrives on GeForce NOW"), and never once the daily pick.
#   policy_regulation — 0 matches in 60 days and 8 of its 9 keywords dead in
#     15 months. Regulation reaches this reader through the labs' own posts,
#     which are not keyword-gated.
RETIRED_TOPIC_IDS = frozenset({"enterprise_deployment", "policy_regulation"})

# Additional keywords that supplement topic-based filtering
_SUPPLEMENTAL_KEYWORDS = [
    # Keep empty — the topic keyword sets above are already high-precision.
]

# Tagging weights. A single substantive keyword ("open-weight", "benchmark")
# outranks any number of brand names, which is the whole point: the item is
# about what it says it is about, not about whose model it mentions.
TOPIC_STRONG_WEIGHT = 10
TOPIC_WEAK_WEIGHT = 1


def _topic_match(topic: dict, text: str) -> tuple[int, int] | None:
    """Score how well `text` fits `topic`, or None when it does not fit.

    Returns (score, longest strong keyword matched). The second element breaks
    ties towards the more specific match, so "coding agent" beats "benchmark"
    on a title carrying both.
    """
    strong = [k for k in topic.get("keywords", ()) if k.lower() in text]
    weak = [k for k in topic.get("weak_keywords", ()) if k.lower() in text]
    if not strong and not weak:
        return None
    score = len(strong) * TOPIC_STRONG_WEIGHT + len(weak) * TOPIC_WEAK_WEIGHT
    return score, max((len(k) for k in strong), default=0)


def score_topics(text: str, topics: list[dict] | None = None) -> list[dict]:
    """Rank the topics `text` matches, best first.

    Ties keep the order of the topic list, which is the order the dashboard
    shows. Replaces the first-match rule that let whichever topic happened to
    be listed first claim every overlapping item.
    """
    candidates = DEFAULT_TOPICS if topics is None else topics
    lowered = (text or "").lower()
    scored = []
    for position, topic in enumerate(candidates):
        match = _topic_match(topic, lowered)
        if match is None:
            continue
        score, longest = match
        scored.append((-score, -longest, position, topic))
    scored.sort()
    return [entry[3] for entry in scored]


def best_topic_id(text: str, topics: list[dict] | None = None) -> str:
    """The id of the topic `text` fits best, or "" when it fits none."""
    ranked = score_topics(text, topics)
    return ranked[0]["id"] if ranked else ""


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
    """Get deduplicated keywords from all active topics, custom keywords, and supplementals.

    Includes each topic's weak keywords: they are weak at *tagging*, not at
    filtering, and the brand names among them are what admit most of the
    Hacker News items that reach the digest at all.
    """
    topics = get_active_topics()
    keywords = set()
    for topic in topics:
        keywords.update(topic["keywords"])
        keywords.update(topic.get("weak_keywords", ()))
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
