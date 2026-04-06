"""Shared pytest fixtures for AI Dev Digest tests."""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def sample_paper():
    """Sample item dictionary."""
    return {
        "title": "GPT-4o mini now available in the API",
        "summary": "OpenAI launches GPT-4o mini with 128K context, function calling, and JSON mode at $0.15/1M input tokens.",
        "url": "https://openai.com/blog/gpt-4o-mini",
        "source": "OpenAI",
        "published": "2024-07-18T00:00:00",
        "type": "announcement",
    }


@pytest.fixture
def sample_papers(sample_paper):
    """List of sample items."""
    return [
        sample_paper,
        {
            "title": "Claude 3.5 Sonnet launches with tool use support",
            "summary": "Anthropic releases Claude 3.5 Sonnet with improved tool use and 200K context window.",
            "url": "https://www.anthropic.com/news/claude-3-5-sonnet",
            "source": "Anthropic",
            "published": "2024-06-20T00:00:00",
            "type": "announcement",
        },
        {
            "title": "Gemini 1.5 Pro available with 1M token context",
            "summary": "Google DeepMind launches Gemini 1.5 Pro with a 1 million token context window via API.",
            "url": "https://deepmind.google/technologies/gemini/pro/",
            "source": "Google DeepMind",
            "published": "2024-05-14T00:00:00",
            "type": "announcement",
        },
    ]


@pytest.fixture
def sample_paper_with_summary(sample_paper):
    """Sample item with generated structured summary."""
    paper = sample_paper.copy()
    paper["why_it_matters"] = "OpenAI released a cost-effective model with 128K context and function calling."
    paper["what_it_is"] = "GPT-4o mini is a smaller, cheaper version of GPT-4o at $0.15/1M input tokens. It supports function calling and JSON mode."
    paper["how_to_use_it"] = "Available now via the OpenAI API using model ID gpt-4o-mini."
    paper["dev_take"] = "Worth testing for high-volume production workloads where cost matters."
    paper["summary"] = "OpenAI released GPT-4o mini, a cost-effective model with 128K context and function calling at $0.15/1M input tokens. Developers can access it via the API immediately."
    return paper


@pytest.fixture
def sample_paper_with_detailed_summary(sample_paper_with_summary):
    """Sample item with detailed summary for PDF."""
    paper = sample_paper_with_summary.copy()
    paper["detailed_summary"] = """**Why it matters**
OpenAI released a cost-effective model with 128K context and function calling.

**What it is**
GPT-4o mini is a smaller, cheaper version of GPT-4o at $0.15/1M input tokens. It supports function calling and JSON mode.

**How to use it**
Available now via the OpenAI API using model ID gpt-4o-mini.

**Dev take**
Worth testing for high-volume production workloads where cost matters."""
    return paper


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"index": 1, "reason": "New model release"}'
    return mock_response


@pytest.fixture
def mock_openai_summary_response():
    """Mock OpenAI API response for summarization."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"why_it_matters": "Cost-effective model release.", "what_it_is": "GPT-4o mini with 128K context.", "how_to_use_it": "pip install openai", "dev_take": "Worth testing."}'
    return mock_response


@pytest.fixture
def mock_blog_feed():
    """Mock blog RSS feed response."""
    return {
        "bozo": False,
        "entries": [
            {
                "title": "Introducing GPT-4o mini API",
                "summary": "OpenAI launches a new affordable model for developers.",
                "link": "https://openai.com/blog/gpt-4o-mini",
                "published": "2024-07-18T00:00:00Z",
                "published_parsed": (2024, 7, 18, 0, 0, 0, 0, 200, 0),
            }
        ],
    }


@pytest.fixture
def env_vars(monkeypatch):
    """Set up required environment variables for testing."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
