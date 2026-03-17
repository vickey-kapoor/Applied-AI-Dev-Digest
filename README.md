# AI Dev Digest

Daily developer-focused updates from Tier 1 AI labs — delivered to your Telegram, explained simply.

## What It Does

- Monitors blog feeds from **OpenAI, Anthropic, Google DeepMind, and Meta AI**
- Filters for **developer-facing product updates** (API changes, SDK releases, new models, pricing, tool launches)
- Uses AI to rank and select the most impactful update
- Generates **ELI5 summaries** anyone can understand
- Sends a daily Telegram message + PDF report
- Includes a **Next.js dashboard** for browsing updates, analytics, and backlog

## Example Message

```
*Daily AI Dev Digest*

*Anthropic launches tool use API for Claude*

You know how apps can look things up or do math for you?
Anthropic just gave Claude the ability to use external
tools — like a calculator or search engine — right inside
API calls. If you're building with Claude, this means your
app can now do way more without extra plumbing.

https://www.anthropic.com/blog/...
_Source: Anthropic_
```

## Setup

### 1. Get API Keys

**Telegram:**
- Create a bot via [BotFather](https://t.me/BotFather) on Telegram
- Save the Bot Token
- Get your Chat ID (send a message to your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`)

**OpenAI:**
- Sign up at [platform.openai.com](https://platform.openai.com/)
- Create an API key (used for ranking & summaries)

### 2. Configure GitHub Secrets

Go to your repository Settings > Secrets and variables > Actions, and add:

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Target Telegram chat ID |
| `OPENAI_API_KEY` | OpenAI API key for ranking & summaries |

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
echo "TELEGRAM_BOT_TOKEN=your_bot_token" >> .env
echo "TELEGRAM_CHAT_ID=your_chat_id" >> .env
echo "OPENAI_API_KEY=your_openai_key" >> .env

# Run
python main.py
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view updates, analytics, reports, and backlog.

## Project Structure

```
ai-research-digest/
├── .github/workflows/
│   └── daily-news.yml          # GitHub Actions (10 AM CST daily)
├── src/
│   ├── constants.py            # Keywords, blog feeds, settings
│   ├── research_fetcher.py     # Aggregates updates from all sources
│   ├── news_ranker.py          # AI-powered update ranking
│   ├── news_summarizer.py      # ELI5 summary generator
│   ├── telegram_sender.py      # Telegram Bot API integration
│   ├── pdf_generator.py        # PDF report generation
│   ├── json_exporter.py        # JSON export for dashboard
│   └── fetchers/
│       └── blog_fetcher.py     # RSS feed fetcher for AI lab blogs
├── dashboard/                  # Next.js dashboard
│   └── src/app/
│       ├── page.tsx            # Home — latest digest
│       ├── papers/             # Browse all updates
│       ├── backlog/            # Updates grouped by AI lab
│       ├── analytics/          # Charts and stats
│       ├── reports/            # PDF reports
│       └── settings/           # Configuration
├── data/                       # JSON data + daily digests
├── reports/                    # Generated PDF reports
├── main.py                     # Entry point
├── requirements.txt
└── README.md
```

## Sources

| Lab | Feed |
|-----|------|
| OpenAI | openai.com/blog |
| Anthropic | anthropic.com |
| Google DeepMind | deepmind.google/blog |
| Meta AI | ai.meta.com/blog |

## License

MIT
