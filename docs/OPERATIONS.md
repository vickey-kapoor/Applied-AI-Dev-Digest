# Operations

Everything needed to run, schedule and deploy the digest. The [README](../README.md) covers what it is.

## Setup

1. **Telegram** — create a bot with [BotFather](https://t.me/BotFather), save the
   token, and get your chat ID from
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
2. **OpenAI** — create an API key at
   [platform.openai.com](https://platform.openai.com/).
3. **Vercel KV** — Storage → Create Database → Upstash KV in any Vercel
   project. Copy `KV_REST_API_URL` and `KV_REST_API_TOKEN` into GitHub
   Secrets. This is the only thing KV is used for: the claim that stops two
   overlapping runs sending the same digest twice.

**GitHub Secrets** (Settings → Secrets → Actions):

| Secret | Notes |
|---|---|
| `TELEGRAM_BOT_TOKEN` | required |
| `TELEGRAM_CHAT_ID` | required |
| `OPENAI_API_KEY` | required — ranking and summaries |
| `KV_REST_API_URL` | required in Actions — the exactly-once send claim |
| `KV_REST_API_TOKEN` | required in Actions — the exactly-once send claim |

`GITHUB_TOKEN` is provided automatically by Actions. Locally, setting one in
`.env` only raises the rate limit for release fetching.

## Models

Ranking and summary use separate models, set in `src/constants.py` and
overridable per step:

| Variable | Effect |
|---|---|
| `OPENAI_MODEL_RANKING` | ranking model (the editorial call) |
| `OPENAI_MODEL_SUMMARY` | summary model |
| `OPENAI_MODEL` | overrides both — the one-line rollback |
| `OPENAI_REASONING_EFFORT` | only for a reasoning model |

The defaults replace `gpt-4o-mini`, which OpenAI has scheduled for shutdown on
14-Jan-2027. The reasoning for the current choices is in the comments at the
top of `src/constants.py`.

## Sources

| Kind | What |
|---|---|
| Blog feeds (RSS) | OpenAI, Google DeepMind, Google AI, Google Research, Meta AI, Mistral, Qwen, Hugging Face, NVIDIA, Together AI |
| Scraped pages | Anthropic news + engineering, OpenAI platform changelog (neither has a usable feed) |
| GitHub releases | openai-python, anthropic-sdk-python, python-genai, transformers, vllm, llama.cpp, mcp/servers |
| Hacker News | Top stories, frontier-lab keywords, score > 100, last 24h, 1 slot |
| Hugging Face | Daily Papers, 20+ upvotes, last 24h |

Lab feeds are not keyword-filtered (publication venue is the signal); the open
sources — HN and HF papers — are, and the corporate-news blocklist applies to
them too. The nine topics are defined in `src/topic_config.py`, which is the
only copy — a TypeScript mirror in the dashboard had to be edited in step and
went with it. All of them are on by default, because a topic that is off also
drops its keywords from the filter. Bare model-family names ("Claude", "GPT-") are `weak_keywords`, which
filter but barely tag.

## Scheduling

`daily-news.yml` polls hourly and `src/schedule_guard.py` decides each tick:

| Condition | Result |
|---|---|
| Already sent today | skip |
| Local time has passed 12:00 | send |
| Target within 3 hours | hold, then send |
| Otherwise | skip |

Scheduled runs on GitHub Actions are best-effort, so an external scheduler
POSTing `workflow_dispatch` at 12:01 local pins delivery to noon; the hourly
hold is the fallback when it doesn't fire. The guard also runs on dispatch, so a
double fire cannot send twice. The target is evaluated in `America/Chicago`, so
noon stays noon across daylight saving. `data/schedule_state.json` records the
last sent date and is committed with the output.

Because a run reads the state file from the commit it started at, the guard
alone cannot settle a tie between a holding tick and a dispatch created
mid-send. The send is therefore gated a second time on a claim in KV that
exactly one run can win — see `src/digest_claim.py`.

Overrides: `DIGEST_TIMEZONE` (`America/Chicago`), `DAILY_TARGET_HOUR` (`12`),
`DAILY_MAX_WAIT_SECONDS` (`10800`).

To run by hand, use **Run workflow** on *Daily Applied AI Dev Digest* in the
Actions tab; the guard still applies unless you tick **force**.

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then add your keys

python main.py                  # run the pipeline
python preview.py               # same fetch and ranking, no send (JSON to stdout)
pytest                          # run the tests
```

**CI** (`.github/workflows/ci.yml`) runs on every PR and on pushes to the
default branch: `pytest` on Python 3.11. Every network and OpenAI call is
mocked, so CI needs no secrets and never sends a digest.

## Layout

```
src/fetchers/   one module per source
src/            ranking, summarizing, article extraction, Telegram, PDF, KV, schedule guard, send claim
data/           digests.json (one entry per day, the already-sent record),
                schedule_state.json (the last date sent)
reports/        generated PDFs, committed by the daily workflow,
                partitioned as reports/YYYY/YYYY-MM-DD/
tests/          pytest suite
docs/           this file
main.py         pipeline entry point
preview.py      local preview
```
