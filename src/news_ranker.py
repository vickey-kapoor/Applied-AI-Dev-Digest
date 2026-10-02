"""Rank AI lab developments by significance using OpenAI."""

import json

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
    )


def _parse_verdict(
    content: str, count: int
) -> tuple[list[int], dict[int, str], list[tuple[int, str]]] | None:
    """Parse the model's keep/reject verdict into 0-based indices.

    Returns (kept_in_order, {index: headline_line}, [(rejected_index, why)]), or
    None if the reply cannot be used at all so the caller can fall back.

    Tolerates the shapes seen in practice: the documented {"keep": [...],
    "reject": [...]}, a {"ranking": [...]} ordering with no rejections, the
    older {"index": N} single pick, and a bare number. An item the model
    mentions in neither list is kept, in its original position — silently
    dropping an item the model never judged would be worse than showing it.
    """
    try:
        parsed = json.loads(content.strip())
    except (json.JSONDecodeError, AttributeError):
        try:
            return [int(content.strip()) - 1], {}, []
        except ValueError:
            return None

    # A bare number parses as valid JSON, so it never reaches the except above.
    if isinstance(parsed, (int, float)) and not isinstance(parsed, bool):
        i = int(parsed) - 1
        return ([i], {}, []) if 0 <= i < count else None

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
        f"[{i+1}] Title: {_sanitize_text(r.get('title', ''), 200)}\nSource: {_sanitize_text(r.get('source', ''), 50)}\nType: {r.get('type', 'announcement')}\nSummary: {_sanitize_text(r.get('summary', ''), 400)}"
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
        if content:
            verdict = _parse_verdict(content, len(items))
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
