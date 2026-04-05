# AI Research Telegram Digest

Get the latest AI developer product updates delivered to your Telegram daily - explained simply, like talking to a friend.

## Features

- Fetches developer product updates from Tier 1 AI lab blogs (OpenAI, Google DeepMind, Meta AI)
- **13 configurable topics** (Core / Applied Domains / Emerging) with toggle UI and custom keywords
- Uses GPT-4o-mini to select the most impactful update, influenced by **user feedback weights**
- Generates **ELI5 summaries** (simple explanations anyone can understand)
- Sends to Telegram via Bot API
- Produces a PDF report and weekly digest roundup
- Exports structured data to JSON (papers + digests)
- Runs automatically via GitHub Actions (10:00 AM CST daily)
- **Pause/resume** digest from the dashboard
- **Send test** button re-sends the last digest to Telegram
- **Digest preview** page runs the pipeline on-demand and shows a Telegram message mockup

## Dashboard

Next.js app deployed on Vercel with top nav: **Topics · Preview · History · Stats · Settings**

| Page | Description |
|------|-------------|
| **Topics** | Toggle 13 research topics on/off, add custom keywords per topic |
| **Preview** | Run the pipeline on-demand, preview the Telegram message, send it |
| **History** | Weekly list of sent papers with 👍/👎 feedback buttons |
| **Stats** | Bar chart showing which topics win the daily ranking most often |
| **Settings** | Data sources, schedule, Telegram config, GitHub Actions link |

All state (topics, pause, feedback, stats) stored in **Vercel KV** (Upstash Redis).

## Example Message

```
*Daily AI Dev Digest*

*Introducing GPT-5.4 mini and nano*

Think of it like a restaurant that just added an express counter.
You still get the same quality food, but there's now a faster,
cheaper option for when you just need a quick bite. Developers
can now build apps that respond quicker and cost less to run.

https://openai.com/index/introducing-gpt-5-4-mini-and-nano
_Lab: OpenAI_
```

## Setup

### 1. Get API Keys

**Telegram:**
- Create a bot via [BotFather](https://t.me/BotFather) on Telegram
- Save the Bot Token
- Get your Chat ID (send a message to your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`)

**OpenAI:**
- Sign up at [platform.openai.com](https://platform.openai.com/)
- Create an API key

**Upstash Redis (for dashboard features):**
- Create a database at [console.upstash.com](https://console.upstash.com)
- Copy the REST URL and REST token

### 2. Configure Secrets

**GitHub Secrets** (Settings > Secrets > Actions):

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Target Telegram chat ID |
| `OPENAI_API_KEY` | OpenAI API key (required for ranking & summaries) |
| `KV_REST_API_URL` | Upstash Redis REST URL (optional — enables dynamic topics) |
| `KV_REST_API_TOKEN` | Upstash Redis REST token (optional — enables dynamic topics) |

**Vercel Environment Variables** (Project Settings > Environment Variables):

Add the same `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` to enable dashboard features (send test, pause, feedback, stats).

### 3. Adjust Schedule (Optional)

Edit `.github/workflows/daily-news.yml` to change the time:

```yaml
schedule:
  - cron: '0 16 * * *'  # 10:00 AM CST (16:00 UTC) daily
```

Use [crontab.guru](https://crontab.guru/) to customize.

## Local Development

```bash
# Clone the repository
git clone https://github.com/vickey-kapoor/ai-research-digest.git
cd ai-research-digest

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your keys
cp .env.example .env
# Edit .env with your API keys

# Run the pipeline
python main.py

# Preview without sending (outputs JSON)
python preview.py

# Run tests
pytest
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev       # Dev server (Turbopack)
npm run build     # Production build
npm run lint      # ESLint
npm test          # Vitest unit tests
```

## Project Structure

```
ai-research-digest/
├── .github/workflows/
│   └── daily-news.yml            # GitHub Actions (daily + weekly)
├── src/
│   ├── fetchers/
│   │   └── blog_fetcher.py       # RSS fetch from AI lab blogs
│   ├── utils/
│   │   └── retry.py              # Retry with exponential backoff
│   ├── ai_text.py                # Prompt sanitization
│   ├── constants.py              # All config constants
│   ├── json_exporter.py          # Atomic JSON export (papers + digests)
│   ├── kv_client.py              # Vercel KV (Upstash Redis) client
│   ├── logger.py                 # Centralized logging
│   ├── news_ranker.py            # GPT-4o-mini ranking + feedback weights
│   ├── news_summarizer.py        # ELI5 summary generation
│   ├── pdf_generator.py          # PDF report generation
│   ├── research_fetcher.py       # Aggregation + deduplication
│   ├── telegram_sender.py        # Telegram Bot API
│   └── topic_config.py           # Dynamic topic config from KV
├── dashboard/                    # Next.js dashboard (Vercel)
│   └── src/
│       ├── app/
│       │   ├── topics/           # Topic toggle UI + custom keywords
│       │   ├── preview/          # Digest preview + Telegram mockup
│       │   ├── history/          # Weekly history + feedback buttons
│       │   ├── stats/            # Topic performance bar chart
│       │   ├── settings/         # Pipeline config overview
│       │   └── api/              # API routes (topics, pause, feedback, etc.)
│       ├── components/
│       │   └── nav.tsx           # Top nav with pause toggle + send test
│       └── lib/
│           ├── topics.ts         # Topic definitions + helpers
│           └── kv.ts             # Shared Redis client
├── data/                         # papers.json + digests.json
├── reports/                      # Generated PDF reports
├── tests/                        # Pytest test suite (160+ tests)
├── main.py                       # Pipeline entry point
├── preview.py                    # Preview pipeline (no Telegram send)
├── weekly_digest.py              # Sunday weekly roundup
└── requirements.txt
```

## Blog Sources

| Source | Feed |
|--------|------|
| OpenAI | openai.com/blog/rss.xml |
| Google DeepMind | deepmind.google/blog/rss.xml |
| Meta AI | engineering.fb.com/feed/ |

## License

MIT
