# Phase 1 Review: Week-1 Audit (2026-05-01 → 2026-05-09)

**Verdict: (B) Starving — fix keyword/threshold tuning before Phase 2**

---

## Daily Run Audit

| Date | papers_fetched | top pick | Source | Topic(s) |
|------|---------------|----------|--------|----------|
| 2026-05-01 | 1 | Research Sabotage in ML Codebases | AI Alignment Forum | Agentic Safety |
| 2026-05-02 | 3 | Risk from fitness-seeking AIs: mechanisms and mitigations | AI Alignment Forum | Alignment, Evals |
| 2026-05-03 | 2 | **null** — no pick selected | — | — |
| 2026-05-04 | 2 | Exploration Hacking: Can LLMs Learn to Resist RL Training? | AI Alignment Forum | Evals, Robustness |
| 2026-05-05 | 2 | GPT-5.5 Instant System Card | OpenAI | System Cards |
| 2026-05-06 | **missing** | no workflow run | — | — |
| 2026-05-07 | **missing** | no workflow run | — | — |
| 2026-05-08 | **missing** | no workflow run | — | — |
| 2026-05-09 | 1 | Running Codex safely at OpenAI | OpenAI | Evals |
| 2026-05-10 | **missing** | no entry yet | — | — |

Week average: **1.8 papers/day** (pre-Phase-1 average was ~9–10/day).

---

## 1. Source Health

**Verdict: broken.** Six of eight configured blog feeds contributed zero items in nine days.

| Source | Items fetched | Top picks |
|--------|--------------|-----------|
| AI Alignment Forum | 3 | 3 |
| OpenAI | 2 | 2 |
| Hacker News | 1 | 0 |
| Anthropic | 0 | 0 |
| Google DeepMind | 0 | 0 |
| Apollo Research | 0 | 0 |
| METR | 0 | 0 |
| Redwood Research | 0 | 0 |
| Center for AI Safety | 0 | 0 |
| HuggingFace | 0 | 0 |

The pipeline is entirely dependent on AI Alignment Forum and OpenAI. The other six BLOG_FEEDS may have broken RSS URLs, low posting cadence, or posts that don't pass FILTER_KEYWORDS. This must be diagnosed before adding Phase 2 sources.

**Three missing workflow days (May 6–8)** are not explained by any digest entry. Either GitHub Actions cron failed silently (check Actions logs for those dates) or the `Validate secrets` step failed and exited non-zero.

**May 3 null pick**: `papers_fetched=2` but `top_paper_id=null` and those two papers do not appear in `data/papers.json`. The items were fetched but neither passed ranking or they were filtered as duplicates of already-sent content. This path produces no Telegram message and no PDF but still commits — silent failure from a subscriber's perspective.

**HuggingFace:** Zero papers all week. The `HF_MIN_UPVOTES=25` threshold is too strict for safety papers. Safety research on HuggingFace rarely goes viral; the prior value of 10 was already borderline. The PR comment acknowledged "if this is too restrictive in practice, tune downward after a week of observation" — one week is enough evidence.

---

## 2. Schema Quality

The structured schema (`claim / evidence / method / limitations / safety_relevance / rigor`) is correctly implemented in `src/news_summarizer.py` and the prompt is well-constructed. However, **the structured fields never reach `data/papers.json`**. In `main.py`, `export_papers()` is called at line 101, then `summarize_research_bundle()` at line 110. The structured fields are added to `top_research` in memory after export, so `papers.json` always contains only the raw RSS description as `summary`. Structured fields reach Vercel KV (`digest:last`, `digest:weekly`) and the PDF, but are unauditable from the repo.

What `papers.json` shows for post-Phase-1 papers:

**Raw feed garbage (bad):**
- *Exploration Hacking* (2026-05-04): `"summary": "We empirically investigate exploration hacking... Authors: Eyon Jang*, Damon Falck*... Paper: arXiv | Code: GitHub | Models: Hugging..."` — trailing HTML/markdown link fragments from the Alignment Forum RSS.
- *Risk from fitness-seeking AIs* (2026-05-02): `"summary": "Current AIs routinely take unintended actions to score well on tasks: hardcoding test cases, training on the test set, downplaying issues..."` — this is the first paragraph of the blog post verbatim, not an analytical summary.

**Empty (worst):**
- *GPT-5.5 Instant System Card* (2026-05-05): `"summary": ""` — a frontier system card is exactly the high-signal item this persona exists for, and it gets an empty string. The RSS item probably had no `<description>`. GPT-4o-mini is called with an empty description and likely returns generic hedging.

The `topic_id` field is also absent from all May papers. The ranker uses `topic_id` for feedback-weight reordering (`src/news_ranker.py` line 52), but fetched items only carry a `topics` list of display names (`["System Cards"]`), not a snake_case `topic_id`. The feedback-weight path silently falls back to the original order for every item.

---

## 3. Coverage Gaps

Cross-checking the audit window against public sources:

- **Anthropic blog** published at least one safety-adjacent post in early May (Claude usage policy updates / model card updates are regular). Zero fetched. Either the Anthropic RSS at `https://www.anthropic.com/news/rss.xml` is not returning recent posts, or posts don't match FILTER_KEYWORDS. Anthropic posts often use "responsible AI" or "trust and safety" language, not the specific safety-vocab keywords in `FILTER_KEYWORDS`. Consider adding `"responsible ai"`, `"trust and safety"`, `"usage policy"`.

- **METR / Apollo Research / Redwood** each post infrequently (weeks between posts), but in a 9-day window there should be at least one item if the feeds are working. Likely cause: RSS URLs need verification — Apollo Research in particular has had feed URL instability.

- **ArXiv cs.AI / cs.LG**: Not in BLOG_FEEDS at all (Phase 2 target). In the audit window, alignment-relevant preprints (e.g., papers on reward model overoptimization, scalable oversight experiments) went untracked. This is expected and correct for Phase 1 scope.

- **Hacker News**: The jailbreak HN post (`"The gay jailbreak technique (2025)"`, 2026-05-02) was fetched but never selected as a top pick, correctly deprioritized by the ranker over empirical AI Alignment Forum posts. HN filtering is working as intended; the source is just producing low-signal items.

---

## 4. HuggingFace Threshold

Zero HuggingFace papers reached top pick in the week. The 25-upvote bar is too high for safety papers. The PR documentation anticipated this: "if this is too restrictive in practice, tune downward." It is. Recommend `HF_MIN_UPVOTES = 10`.

---

## Recommendation: (B) Starving

Fix sourcing before adding Phase 2 complexity.

**Immediate actions:**

1. **`HF_MIN_UPVOTES`: 25 → 10** in `src/constants.py`. One week of zero HF papers is conclusive.

2. **Diagnose silent blog feeds.** Add a startup log in `src/fetchers/blog_fetcher.py` that logs item counts per feed before keyword filtering. Run locally against each BLOG_FEEDS URL to confirm the RSS is reachable and returning recent posts. Apollo Research, METR, CAIS, and Redwood are the suspects.

3. **Widen FILTER_KEYWORDS for Anthropic/OpenAI posts.** Add `"responsible ai"`, `"trust and safety"`, `"usage policy"`, `"safety evaluation"`, `"preparedness"` to `FILTER_KEYWORDS` in `src/constants.py`. Anthropic and OpenAI blog posts use policy language, not the alignment-research vocabulary currently in the keyword list.

4. **Fix the May 6–8 gap.** Check GitHub Actions logs for those dates. If the cron ran and the `Validate secrets` step failed, add a dedicated step that logs "No items found" without exiting with code 1, so the run still commits the digest entry with `papers_fetched=0`.

5. **Minor: move `export_papers` after `summarize_research_bundle`** in `main.py` (lines 101 and 110). This is low-priority but ensures `papers.json` contains the structured fields, making future audits like this one possible without KV access.

Do **not** start Phase 2 (arXiv fetcher, TransformerLens / sae_lens / inspect_ai / garak repos) until the pipeline reliably delivers 5+ items/day. At 1.8 items/day, adding sources risks burying the pipeline's actual feed failures in noise.
