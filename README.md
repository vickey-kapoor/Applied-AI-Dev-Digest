# Applied AI Dev Digest

Daily digest of what's shipping in AI/ML — delivered to Telegram. Tracks blog announcements, GitHub releases, and Hacker News discussions relevant to working ML/AI engineers.

## Features

- Fetches from **8 AI lab/platform blogs** via RSS (OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Microsoft AI, AWS AI, Hugging Face)
- Tracks **10 key GitHub repos** for new releases (transformers, LangChain, vLLM, Ollama, etc.)
- Monitors **Hacker News** for top AI/ML discussions (score > 100, last 24h)
- **10 configurable topics** (Core / Applied / Emerging) with toggle UI and custom keywords
- Uses GPT-4o-mini to select the most impactful item, influenced by **user feedback weights**
- Generates **structured dev summaries** (Why it matters / What it is / How to use it / Dev take)
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
| **Topics** | Toggle 10 dev-focused topics on/off, add custom keywords per topic |
| **Preview** | Run the pipeline on-demand, preview the Telegram message, send it |
| **History** | Weekly list of sent items with feedback buttons |
| **Stats** | Bar chart showing which topics win the daily ranking most often |
| **Settings** | Blog sources, GitHub repos, HN config, schedule, Telegram, Actions link |

All state (topics, pause, feedback, stats) stored in **Vercel KV** (Upstash Redis).

## Example Message

```
#Announcement · OpenAI

*Introducing GPT-5.4 mini and nano*

*Why it matters*
Major price drop for high-volume API users with no quality regression.

*What it is*
GPT-5.4 mini and nano are smaller, cheaper versions of GPT-5.4.
Mini supports 256K context at $0.10/1M input tokens.
Nano is optimized for classification and extraction at $0.03/1M.

*How to use it*
pip install --upgrade openai; use model IDs gpt-5.4-mini or gpt-5.4-nano.

*Dev take*
Worth testing immediately for production workloads where cost matters.

https://openai.com/index/introducing-gpt-5-4-mini-and-nano
```

## Data Sources

### Blog Feeds

| Source | Feed |
|--------|------|
| OpenAI | openai.com/blog/rss.xml |
| Anthropic | anthropic.com/rss.xml |
| Google DeepMind | deepmind.google/blog/rss.xml |
| Meta AI | ai.meta.com/blog/rss/ |
| Mistral | mistral.ai/news/rss |
| Microsoft AI | blogs.microsoft.com/ai/feed/ |
| AWS AI | aws.amazon.com/blogs/machine-learning/feed/ |
| Hugging Face | huggingface.co/blog/feed.xml |

### GitHub Releases

| Repo | Why |
|------|-----|
| huggingface/transformers | Core ML library |
| langchain-ai/langchain | Agent framework |
| run-llama/llama_index | RAG framework |
| vllm-project/vllm | Inference engine |
| ollama/ollama | Local model runner |
| openai/openai-python | OpenAI SDK |
| anthropics/anthropic-sdk-python | Anthropic SDK |
| microsoft/autogen | Multi-agent framework |
| unsloth/unsloth | Fine-tuning |
| ggerganov/llama.cpp | Local inference |

### Hacker News

Top 100 stories filtered by AI/ML keywords, score > 100, last 24 hours. Top 5 returned.

## Topics

| ID | Name | Category | Keywords |
|----|------|----------|----------|
| models | New Model Releases | Core | GPT, Claude, Gemini, Llama, Mistral, model release |
| apis | API & SDK Updates | Core | API, SDK, endpoint, breaking change, deprecation |
| frameworks | Dev Frameworks | Core | LangChain, LlamaIndex, AutoGen, CrewAI, framework |
| inference | Inference & Deployment | Applied | vLLM, Ollama, TensorRT, quantization, serving, deployment |
| finetuning | Fine-tuning & Training | Applied | fine-tuning, LoRA, QLoRA, Unsloth, training, PEFT |
| rag | RAG & Memory | Applied | RAG, retrieval, vector database, embedding, memory |
| agents | AI Agents | Applied | agent, tool use, multi-agent, autonomous, agentic |
| opensource | Open Source Releases | Applied | open source, open weights, Apache, MIT license |
| safety | Safety & Alignment | Emerging | safety, alignment, jailbreak, red-teaming, guardrails |
| hardware | Hardware & Efficiency | Emerging | GPU, TPU, chip, CUDA, inference cost, hardware |

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

`GITHUB_TOKEN` is automatically provided by GitHub Actions — no manual secret needed for release tracking.

**Vercel Environment Variables** (Project Settings > Environment Variables):

Add `KV_REST_API_URL`, `KV_REST_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` to enable dashboard features (send test, pause, feedback, stats).

**For local development:** Set `GITHUB_TOKEN` in `.env` to a personal access token for GitHub release fetching. This is optional — the fetcher works without auth but has lower rate limits.

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
│   │   ├── blog_fetcher.py       # RSS fetch from 8 AI lab/platform blogs
│   │   ├── github_fetcher.py     # GitHub release tracking (10 repos)
│   │   └── hackernews_fetcher.py # HN top stories filtered to AI/ML
│   ├── utils/
│   │   └── retry.py              # Retry with exponential backoff
│   ├── ai_text.py                # Prompt sanitization
│   ├── constants.py              # All config constants
│   ├── fetcher.py                # Source aggregation + URL deduplication
│   ├── json_exporter.py          # Atomic JSON export (papers + digests)
│   ├── kv_client.py              # Vercel KV (Upstash Redis) client
│   ├── logger.py                 # Centralized logging
│   ├── news_ranker.py            # GPT-4o-mini ranking + feedback weights
│   ├── news_summarizer.py        # Structured dev summary generation
│   ├── pdf_generator.py          # PDF report generation
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
├── tests/                        # Pytest test suite (150+ tests)
├── main.py                       # Pipeline entry point
├── preview.py                    # Preview pipeline (no Telegram send)
├── weekly_digest.py              # Sunday weekly roundup
└── requirements.txt
```

## License

MIT
