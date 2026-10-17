"""Rank AI lab developments by significance using OpenAI."""

import json
import re

from openai import OpenAI

from src.ai_text import sanitize_prompt_text
from src.constants import OPENAI_MODEL, OPENAI_MAX_TOKENS_RANKING
from src.logger import get_logger
from src.topic_config import get_feedback_weights
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)
_sanitize_text = sanitize_prompt_text


@retry_with_backoff(exceptions=(Exception,))
def _call_openai_ranking(client: OpenAI, prompt: str):
    """Make an OpenAI API call for ranking with retry logic."""
    return client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=OPENAI_MAX_TOKENS_RANKING,
        temperature=0,
        # Ask for a bare JSON object. Without this the model sometimes wraps
        # the verdict in a ```json fence or opens with a line of prose, which
        # parses as nothing and drops the digest to date order.
        response_format={"type": "json_object"},
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _json_candidates(content: str):
    """Yield the plausible JSON bodies in a reply, most literal first.

    The reply is asked to be a bare JSON object and usually is. When it is
    not, it is wrapped in a markdown fence or preceded by a sentence, and the
    object itself is still intact — worth one more look before giving up,
    because giving up means sending date order.
    """
    text = content.strip()
    yield text

    fenced = _FENCE.search(text)
    if fenced:
        yield fenced.group(1).strip()

    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        yield text[start : end + 1]


def _parse_verdict(
    content: str, count: int
) -> tuple[list[int], dict[int, str], list[tuple[int, str]]] | None:
    """Parse the model's keep/reject verdict into 0-based indices.

    Returns (kept_in_order, {index: headline_line}, [(rejected_index, why)]), or
    None if the reply cannot be used at all so the caller can fall back.

    Tolerates the shapes seen in practice: the documented {"keep": [...],
    "reject": [...]}, a {"ranking": [...]} ordering with no rejections, the
    older {"index": N} single pick, a bare ordering array, and a bare number.
    The body is also found inside a markdown fence or behind a sentence of
    prose, because a reply that is otherwise complete should not cost the day
    its editorial judgement.

    An item the model mentions in neither list is kept, in its original
    position — silently dropping an item the model never judged would be
    worse than showing it.
    """
    if not isinstance(content, str):
        return None

    parsed = None
    for candidate in _json_candidates(content):
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        break

    if parsed is None:
        try:
            return [int(content.strip()) - 1], {}, []
        except ValueError:
            return None

    # A bare number parses as valid JSON, so it never reaches the except above.
    if isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
        i = int(parsed) - 1
        return ([i], {}, []) if 0 <= i < count else None

    # A bare ordering array, with no wrapping object, is the keep list. It is
    # only a verdict if it holds an index, though: a list of strings carries no
    # judgement, and treating it as one would hide an unusable reply behind
    # "every item unjudged, so keep them all" — date order wearing a verdict.
    bare_list = isinstance(parsed, list)
    if bare_list:
        parsed = {"keep": parsed}

    if not isinstance(parsed, dict):
        return None

    def indices(raw):
        """Collect 0-based indices, and any one-line note travelling with them."""
        out, seen, lines = [], set(), {}
        for value in raw if isinstance(raw, list) else []:
            note = ""
            if isinstance(value, dict):
                note = str(value.get("line") or "").strip()
                value = value.get("index")
            try:
                i = int(value) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < count and i not in seen:
                seen.add(i)
                out.append(i)
                if note:
                    lines[i] = note
        return out, lines

    raw_keep = parsed.get("keep")
    if raw_keep is None:
        raw_keep = parsed.get("ranking")
    if raw_keep is None and "index" in parsed:
        raw_keep = [parsed["index"]]
    if raw_keep is None:
        return None

    kept, notes = indices(raw_keep)
    if bare_list and not kept:
        return None

    rejected: list[tuple[int, str]] = []
    for entry in parsed.get("reject") or []:
        idx = entry.get("index") if isinstance(entry, dict) else entry
        why = entry.get("why", "") if isinstance(entry, dict) else ""
        try:
            i = int(idx) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= i < count and i not in kept:
            rejected.append((i, str(why)))

    # Unjudged items are kept rather than dropped.
    judged = set(kept) | {i for i, _ in rejected}
    kept += [i for i in range(count) if i not in judged]
    return kept, notes, rejected


def rank_news(items: list[dict], api_key: str) -> dict | None:
    """Return the single most useful item for an applied AI engineer.

    None when the model judged nothing in the list worth sending. A thin
    wrapper over rank_news_ranked, so the daily message's headlines cost no
    extra model call — one verdict serves both.
    """
    ranked = rank_news_ranked(items, api_key)
    return ranked[0] if ranked else None


# What the ranker is shown per item. The feed summary was the only input here
# and the feeds are not comparable: the Hugging Face blog's carries no
# description at all, Google Research's carries the category label, OpenAI's
# a ~150-character meta description. Items were being rejected for saying
# nothing when it was their feed that had said nothing. main.py now opens
# every candidate's link before ranking, so the article's own opening is
# available; this is how much of it the verdict is worth spending.
#
# Not the whole article: at ~20 candidates the full 12,000-character cap would
# put a quarter of a million characters in one prompt to decide an ordering.
# The opening carries the lede — what shipped, the number, the price — which
# is what this judgement turns on.
RANKING_ARTICLE_CHARS = 900

# The feed summary when there is nothing better.
RANKING_SUMMARY_CHARS = 400


def _describe(item: dict) -> str:
    """The item's labelled text for the ranking prompt, best source first.

    The label is part of the answer: an excerpt that stops mid-sentence reads
    as a truncated article, while the same text under "Summary" reads as a
    complete one that simply says little.

    Sanitization matters more here than it did for feed blurbs — this is the
    body of a third-party web page going into a prompt.
    """
    article = (item.get("article_text") or "").strip()
    if article:
        return f"Article excerpt: {_sanitize_text(article, RANKING_ARTICLE_CHARS)}"
    return f"Summary: {_sanitize_text(item.get('summary', ''), RANKING_SUMMARY_CHARS)}"


def rank_news_ranked(items: list[dict], api_key: str) -> list[dict]:
    """
    Order items by usefulness to an applied AI engineer, most useful first.

    Args:
        items: List of candidate item dictionaries
        api_key: OpenAI API key

    The model also decides what to drop. This is the gate that keyword lists
    were doing badly: no list admits "StreetComplete on iOS is now in public
    beta" while rejecting "Introducing SynthID Bio", but a model asked whether
    an applied engineer should see an item gets both right. Rejections are
    logged with the model's reason so its judgement is visible and tunable.

    Args:
        items: List of candidate item dictionaries
        api_key: OpenAI API key

    Returns:
        The items worth sending, most useful first. Empty if the model rejected
        all of them — a short digest beats a padded one, and the caller sends
        nothing. Falls back to the input order if the model call or its reply
        cannot be used at all.
    """
    if not items:
        raise ValueError("No items to rank")

    if len(items) == 1:
        # A list, not the bare item: this function's contract is a list, and
        # returning the dict here made rank_news index it with [0].
        return list(items)

    # Load feedback weights and reorder by preference before sending to LLM
    try:
        weights = get_feedback_weights()
        if weights:
            # Sort papers so preferred topics come first (higher weight = earlier)
            items = sorted(
                items,
                key=lambda r: weights.get(r.get("topic_id", ""), 1.0),
                reverse=True,
            )
    except Exception:
        pass  # Non-critical — proceed with original order

    client = OpenAI(api_key=api_key)

    # Prepare item summary for the prompt (with sanitization)
    items_text = "\n\n".join(
        f"[{i+1}] Title: {_sanitize_text(r.get('title', ''), 200)}\n"
        f"Source: {_sanitize_text(r.get('source', ''), 50)}\n"
        f"Type: {r.get('type', 'announcement')}\n"
        f"{_describe(r)}"
        for i, r in enumerate(items)
    )

    prompt = f"""You are briefing an applied AI engineer: someone who builds production systems on top of models — serving them, evaluating them, wiring them into agents and products.

Your job is to order today's items by how useful each one is to that person.

Rank by what changes their decisions this week, not by what is most significant to the field in the abstract. A frontier capability they cannot access yet matters less to them than a price cut or a faster runtime they can use today.

Prioritize:
1. Something they can use now — a model, endpoint, or open weight they can call or run today, with the availability, limits and pricing that decide whether it fits
2. Shifts in the cost, latency or quality tradeoffs they build against — price cuts, faster inference, longer context, small models closing the gap
3. Serving and tooling releases that change what is practical to run — inference engines, quantization, frameworks, SDKs — when they carry a real capability or performance change
4. Techniques and patterns with evidence behind them — evals, retrieval, fine-tuning, agent architectures — with numbers rather than claims
5. Measured failure modes and caveats — regressions, benchmark flaws, prompt-injection and reliability findings they would otherwise hit themselves
6. Research whose result changes how to build, not only what is known

Deprioritize:
- Frontier-scale news with nothing to act on — training compute deals, datacenter announcements, capability claims with no access
- Commentary, opinion and speculation rather than a first-party announcement
- Reposts and coverage of something announced days ago
- Hiring, funding rounds, partnerships, leadership, legal and policy news
- Marketing with no model, number, or shipping date
- Pure version bumps with no capability or performance change. A library release carrying a real improvement is NOT this — for this reader a throughput win in an inference engine can outrank a model they cannot access.

Prefer first-party announcements over coverage of them. When two items describe the same thing, pick the one closest to the source.

Items:
{items_text}

First decide, for each item, whether an applied AI engineer should see it at all. Reject anything that is off-domain, pure marketing, a bare version bump, or has nothing they could act on — be willing to reject most of the list, and to reject all of it. A short honest digest beats a padded one.

Collapse duplicate coverage. Several items often describe the same thing in different words — a lab's own post and a news write-up of it, or two outlets on one launch. Keep the one closest to the source and reject the others with why "duplicate of N". Judge this on what the items are about, not on how similar their titles look: "Gemini 4 Argon: our next era of frontier intelligence" and "Google launches Gemini 4" are the same story.

Then order the ones worth keeping, most useful first, and write one line for each.

That line is what the reader sees in a list of headlines, so make it carry the point rather than restate the title. "vLLM v0.12 released" tells them nothing; "vLLM 0.12: 2x throughput on MoE models" tells them whether to click. Lead with the concrete change — a number, a price, a capability, a limit. At most 14 words, no trailing period.

Return JSON:
{{"keep": [{{"index": N, "line": "what it changes, concretely"}}, ...], "reject": [{{"index": N, "why": "a few words"}}, ...], "reason": "one sentence on why the first kept item is the most useful to an applied AI engineer today"}}

Indices are 1-based, and every item must appear in exactly one of the two lists."""

    try:
        response = _call_openai_ranking(client, prompt)

        content = response.choices[0].message.content
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        if content:
            verdict = _parse_verdict(content, len(items))
            if verdict is None:
                # The fallback below is date order, which looks like a working
                # digest. Say so out loud: a verdict cut off by max_tokens
                # ("length") reads exactly like a model that answered badly.
                logger.warning(
                    "Unusable ranking verdict (finish_reason=%s, %d chars) — "
                    "falling back to date order. Reply began: %r",
                    finish_reason,
                    len(content),
                    content[:120],
                )
            if verdict is not None:
                kept, notes, rejected = verdict
                for i, why in rejected:
                    logger.info(
                        "Rejected: %s — %s", items[i].get("title", "")[:70], why or "no reason given"
                    )
                logger.info("Model kept %d of %d candidates", len(kept), len(items))
                # The note rides on the item so the message layer needs no
                # second call to render a headline that carries the point.
                return [
                    {**items[i], "headline_note": notes[i]} if i in notes else items[i]
                    for i in kept
                ]
    except (ValueError, IndexError, TypeError, AttributeError):
        pass
    except Exception:
        logger.error("Failed to rank items with AI")

    # Date order is the honest fallback: it is what fetch_all already produced.
    return list(items)
