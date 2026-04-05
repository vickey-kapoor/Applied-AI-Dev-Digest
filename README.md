# AI Research Telegram Digest

Get the latest AI developer product updates delivered to your Telegram daily - explained simply, like talking to a friend.

## Features

- Fetches developer product updates from Tier 1 AI lab blogs (OpenAI, Google DeepMind, Meta AI)
- Filters for **developer-relevant** content (API launches, model releases, SDK updates)
- Uses GPT-4o-mini to select the most impactful update
- Generates **ELI5 summaries** (simple explanations anyone can understand)
- Sends to Telegram via Bot API
- Produces a PDF report for each digest
- Exports structured data to JSON (papers + digests)
- Runs automatically via GitHub Actions (10:00 AM CST daily)
- Next.js dashboard on Vercel for browsing historical data

## Example Message

```
*Daily AI Research*

*Introducing GPT-5.4 mini and nano*
_OpenAI_

Think of it like a restaurant that just added an express counter.
You still get the same quality food, but there's now a faster,
cheaper option for when you just need a quick bite. Developers
can now build apps that respond quicker and cost less to run.

https://openai.com/index/introducing-gpt-5-4-mini-and-nano
_Source: OpenAI_
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

### 2. Configure GitHub Secrets

Go to your repository Settings > Secrets and variables > Actions, and add:

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Target Telegram chat ID |
| `OPENAI_API_KEY` | OpenAI API key (required for ranking & summaries) |

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

# Run tests
pytest
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev       # Dev server
npm run build     # Production build
npm run lint      # ESLint
npm test          # Vitest unit tests
```

## Project Structure

```
ai-research-digest/
├── .github/workflows/
│   └── daily-news.yml          # GitHub Actions (10 AM CST daily)
├── src/
│   ├── fetchers/
│   │   └── blog_fetcher.py     # RSS fetch from AI lab blogs
│   ├── utils/
│   │   └── retry.py            # Retry with exponential backoff
│   ├── ai_text.py              # Prompt sanitization
│   ├── constants.py            # All config constants
│   ├── json_exporter.py        # Atomic JSON export (papers + digests)
│   ├── logger.py               # Centralized logging
│   ├── news_ranker.py          # GPT-4o-mini ranking
│   ├── news_summarizer.py      # ELI5 summary generation
│   ├── pdf_generator.py        # PDF report generation
│   ├── research_fetcher.py     # Aggregation + deduplication
│   └── telegram_sender.py      # Telegram Bot API
├── dashboard/                  # Next.js dashboard (Vercel)
├── data/                       # papers.json + digests.json
├── reports/                    # Generated PDF reports
├── tests/                      # Pytest test suite
├── main.py                     # Pipeline entry point
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
