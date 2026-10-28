# Applied AI Dev Digest

A daily digest for applied AI engineers, delivered to Telegram at **12:00 noon
America/Chicago**. It answers "what changes what I build this week" rather than
"what matters most to the field", so a callable model, a price shift or a faster
inference engine ranks above a capability no one can access yet.

Every run fetches the day's candidates, has GPT-4o-mini screen, dedupe and rank
them, opens the top link to write a structured brief from the article itself,
and sends that brief plus up to 5 headlines to Telegram. It also writes a PDF
report and appends to `data/papers.json` and `data/digests.json`.

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
them too. 9 topics across Core / Applied are defined in `src/topic_config.py`
and mirrored in `dashboard/src/lib/topics.ts`; keep the two in sync when
editing. All of them are on by default, because a topic that is off also drops
its keywords from the filter. An item is tagged with the topic it fits best,
scored over matched keywords, rather than the first one listed; bare model-family
names ("Claude", "GPT-") are `weak_keywords`, which filter but barely tag.

## Dashboard

Next.js app on Vercel: **Topics · Preview · History · Stats · Settings** — toggle
topics and keywords, see the last digest as a Telegram mockup and re-send it,
give thumbs up/down on past items (which reweights ranking), view topic stats,
and pause or resume the digest. State lives in Vercel KV (Upstash Redis).

## Setup

1. **Telegram** — create a bot with [BotFather](https://t.me/BotFather), save the
   token, and get your chat ID from
   `https://api.telegram.org/bot<TOKEN>/getUpdates`.
2. **OpenAI** — create an API key at
   [platform.openai.com](https://platform.openai.com/).
3. **Vercel KV** — in your Vercel project, Storage → Create Database → Upstash
   KV. Vercel sets `KV_REST_API_URL` and `KV_REST_API_TOKEN`; copy the same
   values into GitHub Secrets.

**GitHub Secrets** (Settings → Secrets → Actions):

| Secret | Notes |
|---|---|
| `TELEGRAM_BOT_TOKEN` | required |
| `TELEGRAM_CHAT_ID` | required |
| `OPENAI_API_KEY` | required — ranking and summaries |
| `KV_REST_API_URL` | optional — enables dynamic topics |
| `KV_REST_API_TOKEN` | optional — enables dynamic topics |

`GITHUB_TOKEN` is provided automatically by Actions. Locally, setting one in
`.env` only raises the rate limit for release fetching.

**Vercel env vars**: add `KV_REST_API_URL`, `KV_REST_API_TOKEN`,
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` for the dashboard features.

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

Overrides: `DIGEST_TIMEZONE` (`America/Chicago`), `DAILY_TARGET_HOUR` (`12`),
`DAILY_MAX_WAIT_SECONDS` (`10800`).

To run by hand, use **Run workflow** on *Daily Applied AI Dev Digest* in the
Actions tab; the guard still applies unless you tick **force**.

## Local development

```bash
git clone https://github.com/vickey-kapoor/Applied-AI-Dev-Digest.git
cd Applied-AI-Dev-Digest
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then add your keys

python main.py                  # run the pipeline
python preview.py               # preview without sending (JSON to stdout)
pytest                          # run the tests
```

Dashboard:

```bash
cd dashboard
npm install
npm run dev     # dev server
npm run build   # production build
npm run lint    # ESLint
npm test        # Vitest
```

**CI** (`.github/workflows/ci.yml`) runs on every PR and on pushes to `master`:
`pytest` on Python 3.11, plus `tsc --noEmit`, `npm run lint` and `npm test` for
the dashboard. Every network and OpenAI call is mocked, so CI needs no secrets
and never sends a digest.

## Layout

```
src/fetchers/   one module per source
src/            ranking, summarizing, article extraction, Telegram, PDF, KV, schedule guard
dashboard/      Next.js dashboard (Vercel)
data/           papers.json, digests.json, schedule_state.json
reports/        generated PDFs
tests/          pytest suite
main.py         pipeline entry point
preview.py      local preview
```

## License

MIT
