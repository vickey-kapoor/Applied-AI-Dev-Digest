"""Dynamic topic configuration backed by Vercel KV."""

import re

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
# alike. The audit report is audits/2026-10-28-topics-audit.md in the
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
        # Brand names: the gate's workhorses, and deliberately weak at tagging,
        # except when the title names a *version* of the model — see
        # MODEL_NAME_PATTERNS. "Command R" is gone — no match in 500 items.
        "weak_keywords": [
            "GPT-", "Claude", "Gemini", "Llama", "Mistral", "Qwen",
            "DeepSeek", "Grok", "Gemma",
        ],
        # A brand name in a title that also names a version is naming a
        # release, so it scores as strong there and only there.
        "promote_weak_on_model_version": True,
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
        # The four API-lifecycle terms were added by the 31-Oct-2026 re-audit:
        # the OpenAI and Anthropic platform changelogs are this topic's main
        # suppliers and two of their entries had already been daily picks
        # while carrying no topic at all ("12-hour prompt caching in the API",
        # "which service tiers projects can use").
        "keywords": [
            "responses api", "context window", "context length", "deprecat",
            "prompt caching", "usage tier", "service tier", "legacy api",
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
            "fine-tun", "continual learning", "federated", "foundation model",
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
            "agent framework", "agent harness",
        ],
        # The two coding agents by name. Weak, because a customer story that
        # merely mentions Codex is not an agents post; strong enough to beat a
        # bare brand name, which is what filed "Backdoor in Claude Code for VS
        # Code extension" under Model Releases in the 30-Oct-2026 digest.
        "weak_keywords": ["Claude Code", "Codex"],
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
            "interpretability", "model spec", "independent evaluator",
            "watermark", "safeguard",
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
            "Hugging Face release", "OLMo", "open-sourc",
        ],
        "default_enabled": True,
    },
    {
        "id": "infrastructure",
        "name": "Compute & Infrastructure",
        # "TPU" was removed by the 31-Oct-2026 re-audit: all 12 of its hits
        # in 500 items are the letters inside the word *output*, the same
        # substring trap that cost us "serving"/*preserving*. Google's silicon
        # reaches this topic through "inference" and the lab's own blog.
        "keywords": [
            "inference", "quantiz", "gpu cluster", "Blackwell",
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
            "world simulation", "transcri", "ASR", "text-to-image",
            "diffusers", "prompt-to-voice",
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
# A title that names a model version is the most reliable signal in the whole
# taxonomy — 69 firings over 500 pooled items, every one of them a specific
# model — so it outranks a single ordinary keyword rather than tying with it.
# Without that, "Released GPT-6.1 Terra, a fast, efficient model for visual
# reasoning" lost Model Releases to Product & API on the phrase "context
# length" further down its changelog entry.
TOPIC_MODEL_NAME_WEIGHT = 15

# Model families whose names, in a *title*, name a released model rather than
# merely mention a vendor. Scoring a brand name weak stopped it outvoting a
# topic that matched on substance (the 28-Oct-2026 audit), but it did nothing
# for the much larger group where no other topic matched at all: 68 of
# model_releases' 88 tags in the following 60 days were still decided by a
# brand name alone, among them "Swedish government offices to ban ChatGPT and
# Claude", "anthropic-sdk-python v2.3.0 released" and "Backdoor in Claude Code
# for VS Code extension", which went out on 30-Oct-2026 tagged #ModelRelease.
#
# What separates a release from a mention is a version: "Claude Haiku 5.5",
# "GPT-6.1 Terra", "Mistral Large 4". These two patterns look for a family
# name followed by up to two product words and then a number, or a family name
# hyphenated to a capitalised codename ("GPT-Rosalind"). Over all 500 pooled
# items they fire on 69 titles, every one of which names a specific model.
# They are deliberately conservative about prose: "DeepSeek launching v4.1
# flash" is a release and is missed, because requiring the intervening words
# to be capitalised is what keeps "Mistral raises €3B" out.
#
# The client-library exclusion matters: "llama.cpp v0.8.0 released" and
# "anthropic-sdk-python v2.3.0" are version numbers attached to a package, not
# a model, and the release notes under them name every model the library
# gained support for. Matching the title alone, and refusing these suffixes,
# keeps a dozen library bumps out of Model Releases.
_MODEL_FAMILIES = (
    r"gpt|claude|gemini|llama|mistral|qwen|deepseek|grok|gemma|olmo"
    r"|nemotron|granite|falcon|apertus|flux"
)
_NOT_A_LIBRARY = r"(?![a-z0-9]*(?:\.cpp|[-.](?:python|js|go|cpp|rs)|-sdk))"
MODEL_NAME_PATTERNS = (
    re.compile(
        r"(?<![A-Za-z0-9])(?i:" + _MODEL_FAMILIES + r")" + _NOT_A_LIBRARY
        # Up to two product words — "Large", "Haiku", "Flash Next" — which must
        # be capitalised. That is what separates "Mistral Large 4" from
        # "Mistral raises €3B": a lowercase verb is prose, not a model name.
        + r"(?:[-\s][A-Z][A-Za-z.]{0,12}){0,2}[-\s]?v?\d",
    ),
    # "GPT-Rosalind", "Claude-Mythos": a codename, not a number. Capitalisation
    # is the signal here, so only the family name is matched case-insensitively.
    re.compile(r"(?<![A-Za-z0-9])(?i:gpt|claude|gemini)-" + _NOT_A_LIBRARY + r"[A-Z][a-z]{2,}"),
)


def names_a_model_version(title: str) -> bool:
    """True when `title` names a specific model version, not just a vendor."""
    return any(p.search(title or "") for p in MODEL_NAME_PATTERNS)


def _topic_match(
    topic: dict, text: str, promote_weak: bool = False
) -> tuple[int, int] | None:
    """Score how well `text` fits `topic`, or None when it does not fit.

    Returns (score, longest keyword matched). The second element breaks ties
    towards the more specific match, so "coding agent" beats "benchmark" on a
    title carrying both, and "Claude Code" beats a bare "Claude".

    `promote_weak` scores this topic's weak keywords as strong. It is set for
    the topics carrying `promote_weak_on_model_version` when the title names a
    model version — see MODEL_NAME_PATTERNS.
    """
    strong = [k for k in topic.get("keywords", ()) if k.lower() in text]
    weak = [k for k in topic.get("weak_keywords", ()) if k.lower() in text]
    if not strong and not weak:
        return None
    # A topic whose weak keywords are vendor names does not get to claim an
    # item on a vendor name alone. Without this, "Mistral raises EUR 3B" and
    # "Claude partial outage" are Model Releases, because nothing else in the
    # taxonomy matches them and a score of 1 still beats no score at all.
    # Every other topic's weak keywords may still tag: "Claude Code" and
    # "Codex" name agent tooling whatever else the sentence is about.
    if not strong and not promote_weak and topic.get(
        "promote_weak_on_model_version", False
    ):
        return None
    weak_weight = TOPIC_MODEL_NAME_WEIGHT if promote_weak else TOPIC_WEAK_WEIGHT
    score = len(strong) * TOPIC_STRONG_WEIGHT + len(weak) * weak_weight
    longest = max((len(k) for k in strong + weak), default=0)
    return score, longest


def score_topics(
    text: str, topics: list[dict] | None = None, title: str | None = None
) -> list[dict]:
    """Rank the topics `text` matches, best first.

    Ties keep the order of the topic list, which is the order the dashboard
    shows. Replaces the first-match rule that let whichever topic happened to
    be listed first claim every overlapping item.

    `title` is the item's title on its own. Callers that have it should pass
    it: it is what decides whether a brand name is naming a released model or
    only mentioning its vendor. Without it no weak keyword is ever promoted,
    so omitting it is safe but loses accuracy on Model Releases.
    """
    candidates = DEFAULT_TOPICS if topics is None else topics
    lowered = (text or "").lower()
    versioned = names_a_model_version(title) if title else False
    scored = []
    for position, topic in enumerate(candidates):
        promote = versioned and topic.get("promote_weak_on_model_version", False)
        match = _topic_match(topic, lowered, promote)
        if match is None:
            continue
        score, longest = match
        scored.append((-score, -longest, position, topic))
    scored.sort()
    return [entry[3] for entry in scored]


def best_topic_id(
    text: str, topics: list[dict] | None = None, title: str | None = None
) -> str:
    """The id of the topic `text` fits best, or "" when it fits none."""
    ranked = score_topics(text, topics, title)
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
