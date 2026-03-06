# AI News WhatsApp Alert

Get the most important AI news delivered to your WhatsApp daily.

## Features

- Fetches latest AI/ML news from NewsAPI
- Uses AI (GPT-4o-mini) to select the most impactful story
- Sends formatted message to WhatsApp via Twilio
- Runs automatically via GitHub Actions

## Setup

### 1. Get API Keys

**NewsAPI:**
- Sign up at [newsapi.org](https://newsapi.org/)
- Get your free API key

**Twilio:**
- Sign up at [twilio.com](https://www.twilio.com/)
- Get Account SID and Auth Token from Console
- Set up WhatsApp Sandbox: [Twilio WhatsApp Sandbox](https://www.twilio.com/console/sms/whatsapp/sandbox)
- Send "join <sandbox-code>" from your WhatsApp to the Twilio number

**OpenAI (Optional but recommended):**
- Sign up at [platform.openai.com](https://platform.openai.com/)
- Create an API key

### 2. Configure GitHub Secrets

Go to your repository Settings > Secrets and variables > Actions, and add:

| Secret | Description |
|--------|-------------|
| `NEWS_API_KEY` | Your NewsAPI key |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Twilio WhatsApp number (e.g., `whatsapp:+14155238886`) |
| `YOUR_WHATSAPP_NUMBER` | Your WhatsApp number (e.g., `whatsapp:+1234567890`) |
| `OPENAI_API_KEY` | OpenAI API key (optional) |

### 3. Adjust Schedule (Optional)

Edit `.github/workflows/daily-news.yml` to change the time:

```yaml
schedule:
  - cron: '0 8 * * *'  # 8:00 AM UTC daily
```

Use [crontab.guru](https://crontab.guru/) to customize.

## Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-news-whatsapp-alert.git
cd ai-news-whatsapp-alert

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run
python main.py
```

## Project Structure

```
ai-news-whatsapp-alert/
├── .github/
│   └── workflows/
│       └── daily-news.yml    # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── news_fetcher.py       # Fetch news from NewsAPI
│   ├── news_ranker.py        # AI-powered news ranking
│   └── whatsapp_sender.py    # Twilio WhatsApp integration
├── main.py                   # Entry point
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
