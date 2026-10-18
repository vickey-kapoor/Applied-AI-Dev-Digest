"""Centralized constants for AI Dev Digest."""

import os

# Application info
APP_NAME = "AI Dev Digest"
APP_VERSION = "2.0.0"
# Sent by every fetcher so feed and API operators can identify the client.
# The repo slug was wrong here (ai-research-digest) while nothing used the
# value; corrected now that it is actually on the wire.
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (+https://github.com/vickey-kapoor/Applied-AI-Dev-Digest)"

# Network settings
REQUEST_TIMEOUT = 30  # seconds
# MAX_RETRIES removed: it claimed 3 while every call site passed 2. The
# retry_with_backoff default is now 2 to match, so call sites no longer
# override it and there is one place left that says how many retries happen.

# Deduplication settings
DEDUP_SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.85"))

# Digest settings
# Candidates handed to the ranker. The final truncation is date-ordered, so
# this is not a quality cut — at 10, with the pool restored to ~20 real
# candidates, genuinely better items were being dropped for being 40 hours old
# rather than 4. The ranker is the editorial filter; it needs to see the pool.
DIGEST_MAX_RESULTS = int(os.getenv("DIGEST_MAX_RESULTS", "20"))

# Maximum age of an item eligible for the daily pick. Blog feeds carry no
# recency cutoff of their own (HN, HF and GitHub each cut at 24h), so without
# this a quiet day could surface a week-old post as "today's" development.
# 72h rather than 24h because labs post far less often than HN churns — a
# Friday launch should still be eligible on Monday. Repeats are not a risk:
# get_sent_top_paper_ids() filters anything already sent as a top pick.
DIGEST_MAX_AGE_HOURS = int(os.getenv("DIGEST_MAX_AGE_HOURS", "72"))

# OpenAI model settings
#
# Two calls a day, so the bill is not what picks the model: the whole pipeline
# ran at about 8.5 cents a month on gpt-4o-mini. What picks it is that the two
# calls are not the same job. Ranking is the hard one — screen ~20 candidates
# on their article text, collapse duplicate coverage of one announcement, and
# order what is left by use to an applied engineer. Summarizing is extraction
# from a single article the ranker already chose.
#
# Both steps ran on gpt-4o-mini, which is deprecated: OpenAI's deprecations
# page dated 14-Oct-2026 gives gpt-4o-mini-2024-07-18 a shutdown date of
# 14-Jan-2027 and names gpt-6-luna as its replacement. So the defaults below
# are the replacements, one per step rather than one for both.
#
# gpt-6.1-sol for ranking: that call is the digest's editorial judgement and
# the only one whose mistakes the reader sees as a bad pick. At $2/$10 per
# million tokens and one call a day it runs around a dollar a month, against
# eight cents for the whole pipeline before. gpt-6-luna for the summary, at
# $0.10/$0.50 — extraction from one article the ranker already chose, and
# cheaper than the gpt-4o-mini it replaces.
#
# Both are reasoning models, which is why the ceilings below are generous and
# why openai_call drops an argument the model will not take: the generations
# disagree about temperature and about the ceiling's own name.
#
# Every one of these is an environment variable, passed through from a
# repository variable, so a model is changed and changed back in the
# repository's settings rather than in a commit. `python preview.py` runs both
# calls and prints the result without sending anything, which is how to look
# at a candidate's output before a daily run uses it.
#
# `or` rather than a getenv default throughout: the workflow passes these
# through from repository variables, and an unset GitHub variable arrives as
# an empty string rather than as nothing at all.

# Both steps at once — the one-line rollback, e.g. OPENAI_MODEL=gpt-4o-mini
# while that model still answers. Unset by default; the per-step defaults win.
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or ""
OPENAI_MODEL_RANKING = (
    os.getenv("OPENAI_MODEL_RANKING") or OPENAI_MODEL or "gpt-6.1-sol"
)
OPENAI_MODEL_SUMMARY = (
    os.getenv("OPENAI_MODEL_SUMMARY") or OPENAI_MODEL or "gpt-6-luna"
)

# Zero, not 0.7: the summarizer extracts stated facts — model names, prices,
# context lengths — from an article. Sampling variance there buys nothing and
# costs accuracy, and the prompt already tells the model to write "Not stated"
# rather than guess. Sent only when the model accepts it: the reasoning models
# reject temperature, and openai_call drops an argument the model refuses.
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE") or 0)

# Reasoning effort, for a model that has one. Unset by default so each model
# keeps its own default; openai_call drops it for a model that has none.
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT") or None

# Ceiling on each reply, not a target — an unused ceiling costs nothing, since
# output is billed on what the model writes.
#
# These were sized to the visible answer: 150 when the ranking reply was
# {"index": N}, then 1200 when PR #30 found 150 truncating a verdict that had
# grown a line per kept item and a reason per rejected one. Sizing a ceiling to
# the answer is the bug, not the number — it has now been wrong twice, both
# times silently, because truncated JSON does not parse and the ranker's
# fallback is date order, which reads as a working digest.
#
# A reasoning model makes that worse: its reasoning tokens are billed as output
# and come out of this same ceiling before it writes a visible character, so a
# ceiling sized for the answer returns no answer at all. These are now set near
# the output limit of the smallest model in play (gpt-4o-mini caps at 16,384)
# and are not meant to be reached.
OPENAI_MAX_TOKENS_RANKING = int(os.getenv("OPENAI_MAX_TOKENS_RANKING") or 16000)
# OPENAI_MAX_TOKENS_SUMMARY and _DETAILED removed: superseded when the
# summarizer moved to a single bundled call using _BUNDLE below.
OPENAI_MAX_TOKENS_BUNDLE = int(os.getenv("OPENAI_MAX_TOKENS_BUNDLE") or 16000)

# Telegram settings
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Data cap settings
PAPERS_CAP = 500
DIGEST_CAP_DAYS = 90

# Thread pool settings
THREAD_POOL_WORKERS = 2

# Persona: engineer/researcher tracking what the frontier AI labs ship.
# Default keyword set — broad lab-development vocabulary used as a fallback when
# no topic-config keywords are passed through. Topic-level filtering (in
# topic_config.DEFAULT_TOPICS) is the primary signal.
#
# Keywords are matched as case-insensitive substrings against title + summary,
# so avoid short tokens that hide inside common words (e.g. "api" matches
# "rapid"). Prefer multi-word identifiers.
# FILTER_KEYWORDS removed. Its only consumer was the blog fetcher's topic gate,
# which is gone: a post on a frontier lab's own feed is an AI development
# because of where it was published, and requiring a keyword there dropped real
# launches. The open sources carry their own lists — HN_KEYWORDS for Hacker
# News — and fetch_all passes the live topic keywords from KV, so nothing read
# this constant any more.

# Keywords to exclude non-technical corporate news (lowercase)
EXCLUDE_KEYWORDS = [
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
    "lawsuit",
    "trademark",
]

# No off-domain blocklist here. Corporate feeds do carry consumer and marketing
# content — NVIDIA's is the whole company blog — but keeping a literal list of
# the junk ("geforce", "xprize") was whack-a-mole that could only ever catch
# what had already shipped. The ranker now screens every candidate and rejects
# what an applied engineer should not see, which is a judgement no word list
# makes correctly. The entries above stay because they are cheap, uncontentious
# and save the model tokens; they are not the editorial gate.

# Tutorial and how-to shapes, matched against the TITLE ONLY.
# Deliberately not folded into EXCLUDE_KEYWORDS: that list is checked against
# title + summary, and phrases like "how to" appear legitimately in the body of
# real release posts ("we show how to call the new endpoint"). Restricting
# these to the title keeps vendor walkthroughs out without dropping launches.
EXCLUDE_TITLE_PATTERNS = [
    "part 1", "part 2", "part 3", "part one", "part two",
    "how to", "how we built", "getting started", "step-by-step",
    "step by step", "walkthrough", "tutorial", "a guide to",
    "best practices", "tips and tricks", "deep dive into",
    "build a ", "building a ", "build agentic", "create a ",
]

# No single source may take more than this many slots in the candidate pool.
# A high-volume vendor blog otherwise crowds out the frontier labs: on 28-Aug
# one such feed held 4 of 10 slots and won the daily pick with a how-to post.
MAX_ITEMS_PER_SOURCE = int(os.getenv("MAX_ITEMS_PER_SOURCE", "2"))

# Blog RSS feeds — frontier AI labs and the platforms they ship on.
# Every URL here was verified to return a parseable feed. Anthropic has no feed
# at all, so it is not here: ANTHROPIC_LISTINGS below reads its pages instead.
BLOG_FEEDS = {
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "Google Research": "https://research.google/blog/rss/",
    "Meta AI": "https://engineering.fb.com/category/ml-applications/feed/",
    "Mistral AI": "https://mistral.ai/rss.xml",
    # "Hugging Face Blog", not "Hugging Face": the Daily Papers fetcher already
    # reports the latter, and one name for a curated lab feed and an aggregator
    # makes the two indistinguishable to any per-source rule.
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "NVIDIA": "https://blogs.nvidia.com/feed/",
    "Together AI": "https://www.together.ai/blog/rss.xml",
    # EleutherAI removed: blog.eleuther.ai/{index,rss,feed}.xml and
    # eleuther.ai/index.xml all 404, so the feed contributed nothing but a
    # parse-error warning on every run.
    # Qwen removed: qwenlm.github.io/blog/index.xml still parses, but its
    # newest entry is 23-Sep-2025 — the team moved to qwen.ai, which is
    # client-rendered and serves the SPA shell for /rss.xml, /index.xml and
    # /blog alike, so there is no feed to point at. The feed was contributing
    # "0 within 72h" on every run while reading as a live source. Qwen
    # releases still reach the digest through Hacker News (HN_KEYWORDS lists
    # "Qwen") and the Hugging Face blog.
}

# OpenAI's developer changelog, scraped rather than fetched as a feed.
#
# It is here and not in BLOG_FEEDS because it is not a feed: one server-rendered
# page holds every entry, with no RSS and no per-entry permalink. It exists in
# the project because openai.com/index/* — the news blog those RSS entries point
# at — answers 403 to every non-browser client, with `cf-mitigated: challenge`
# and a Sec-CH-UA client-hint demand, so the only OpenAI text reaching the
# summarizer was the feed's ~150-character meta description. The changelog is
# unchallenged and, for an applied engineer, more useful: model releases with
# their token prices, new service tiers, and bugs worth re-running evals over.
OPENAI_CHANGELOG_URL = "https://platform.openai.com/docs/changelog"

# A source name of its own, not "OpenAI". Two reasons: the per-source cap would
# otherwise make the changelog and the news blog compete for the same two slots,
# and CURATED_SOURCES membership is per name.
OPENAI_CHANGELOG_SOURCE = "OpenAI Platform"

# The page carries 35 months of history. Only the newest entries can be inside
# the recency window, and the central cap trims further.
OPENAI_CHANGELOG_MAX_ITEMS = int(os.getenv("OPENAI_CHANGELOG_MAX_ITEMS", "15"))

# Anthropic's own posts, scraped rather than fetched as a feed.
#
# Anthropic published 1 item into this digest's whole history, against 179 from
# Hacker News, because it has no feed: /rss.xml, /feed.xml, /index.xml and the
# per-section variants all 404. The listing pages are server-rendered and
# robots.txt says `Allow: /`, so they are read directly. Unlike openai.com/index/*
# the post pages answer 200 to a plain client, and the summarizer gets 7,000 to
# 12,000 characters from them rather than a meta description.
#
# Two sources, not one, for the same reason the OpenAI changelog is separate
# from the OpenAI blog: /news is mostly policy, partnerships and offices, while
# /engineering is the applied-engineering writing this reader is here for. Under
# one name the per-source cap of 2 would let a week of policy posts crowd the
# engineering post out.
ANTHROPIC_SOURCE = "Anthropic"
ANTHROPIC_ENGINEERING_SOURCE = "Anthropic Engineering"

# listing URL -> (source name, path prefix for a post's permalink).
# A post tagged both News and Research resolves under either prefix — both
# /news/alignment-faking and /research/alignment-faking return the same page —
# so the listing a post was found on always gives a working URL.
ANTHROPIC_LISTINGS = {
    "https://www.anthropic.com/news": (ANTHROPIC_SOURCE, "/news/"),
    "https://www.anthropic.com/engineering": (ANTHROPIC_ENGINEERING_SOURCE, "/engineering/"),
}

# The news listing embeds its whole archive — 276 posts on 17-Oct-2026 — so the
# newest few are the only ones that can be inside the recency window, and the
# central per-source cap trims further.
ANTHROPIC_MAX_ITEMS = int(os.getenv("ANTHROPIC_MAX_ITEMS", "15"))

# Minimum candidate posts pulled per blog feed before keyword filtering.
# Without a floor, adding feeds shrinks each feed's share to a single post,
# so a lab that posted a few consumer items ahead of its release loses it.
# The feed is fetched in full either way, so this costs no extra requests.
# Safety bound only, not a selection rule: the blog fetcher selects by
# publication date, and this exists so one pathological feed cannot flood the
# candidate pool. It replaced a hard count of 5 that silently capped what was
# even considered, turning 2,593 available entries into 55.
BLOG_MAX_PER_SOURCE = int(os.getenv("BLOG_MAX_PER_SOURCE", "20"))

# GitHub repos whose releases mark a shipped lab development — official model
# SDKs plus the serving/runtime stacks new models land in first.
GITHUB_REPOS: list[str] = [
    "openai/openai-python",
    "anthropics/anthropic-sdk-python",
    "googleapis/python-genai",
    "huggingface/transformers",
    "vllm-project/vllm",
    "ggml-org/llama.cpp",
    "modelcontextprotocol/servers",
]

# Hacker News filter keywords — frontier lab launches and announcements.
# This is the primary channel for Anthropic news, which has no RSS feed.
HN_KEYWORDS = [
    # Labs by name
    "OpenAI", "Anthropic", "Claude", "GPT-", "DeepMind", "Gemini",
    "Mistral", "Qwen", "DeepSeek", "Llama", "Grok", "xAI", "Gemma",
    # Release language
    "model release", "new model", "frontier model", "reasoning model",
    "open weights", "open-weight", "system card", "technical report",
    # Capability surfaces
    "agentic", "computer use", "function calling", "model context protocol",
    "long context", "multimodal", "benchmark", "SWE-bench", "ARC-AGI",
    # Infra
    "inference", "TPU", "Blackwell", "training run",
]
HN_MIN_SCORE = 100
HN_MAX_STORIES = 5

# Hugging Face Daily Papers — lab research lands here first. Kept moderately
# permissive so lab technical reports surface the day they drop.
HF_MIN_UPVOTES = 20
HF_MAX_PAPERS = 5

# Dashboard history list (KV key `digest:weekly`) — one entry per digest sent.
# The Sunday roundup used to clear this list each week; with the roundup gone
# the append side caps it, so the History page stays a bounded read.
HISTORY_MAX_ENTRIES = int(os.getenv("HISTORY_MAX_ENTRIES", "90"))
