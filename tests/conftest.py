"""Shared pytest fixtures for AI Dev Digest tests."""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def sample_paper():
    """Sample product update dictionary."""
    return {
        "title": "GPT-4o mini now available in the API",
        "description": "OpenAI launches GPT-4o mini with 128K context, function calling, and JSON mode at $0.15/1M input tokens.",
        "source": "OpenAI",
        "lab": "OpenAI",
        "url": "https://openai.com/blog/gpt-4o-mini",
        "published_at": "2024-07-18T00:00:00",
        "type": "product_update",
        "authors": "OpenAI",
        "topics": ["Model Release", "API Update"],
    }


@pytest.fixture
def sample_papers(sample_paper):
    """List of sample product updates."""
    return [
        sample_paper,
        {
            "title": "Claude 3.5 Sonnet launches with tool use support",
            "description": "Anthropic releases Claude 3.5 Sonnet with improved tool use and 200K context window.",
            "source": "Anthropic",
            "lab": "Anthropic",
            "url": "https://www.anthropic.com/news/claude-3-5-sonnet",
            "published_at": "2024-06-20T00:00:00",
            "type": "product_update",
            "authors": "Anthropic",
            "topics": ["Model Release", "Function Calling"],
        },
        {
            "title": "Gemini 1.5 Pro available with 1M token context",
            "description": "Google DeepMind launches Gemini 1.5 Pro with a 1 million token context window via API.",
            "source": "Google DeepMind",
            "lab": "Google DeepMind",
            "url": "https://deepmind.google/technologies/gemini/pro/",
            "published_at": "2024-05-14T00:00:00",
            "type": "product_update",
            "authors": "Google DeepMind",
            "topics": ["Model Release", "API Update"],
        },
    ]


@pytest.fixture
def sample_paper_with_summary(sample_paper):
    """Sample update with generated summary."""
    paper = sample_paper.copy()
    paper["summary"] = "OpenAI released GPT-4o mini, a cost-effective model with 128K context and function calling at $0.15/1M input tokens. Developers can access it via the API immediately."
    return paper


@pytest.fixture
def sample_paper_with_detailed_summary(sample_paper_with_summary):
    """Sample update with detailed summary for PDF."""
    paper = sample_paper_with_summary.copy()
    paper["detailed_summary"] = """**What Was Announced**

OpenAI launched GPT-4o mini, a smaller and more affordable version of GPT-4o designed for high-volume developer use cases.

**Technical Capabilities**

The model supports a 128K context window, function calling, and JSON mode. Pricing is set at $0.15 per million input tokens and $0.60 per million output tokens, making it significantly cheaper than GPT-4o.

**Getting Started**

Developers can access GPT-4o mini immediately through the OpenAI API using the model ID 'gpt-4o-mini'. No waitlist or special access required.

**How It Compares**

GPT-4o mini competes directly with Claude 3 Haiku and Gemini 1.5 Flash in the fast-and-cheap model tier, offering strong performance at a competitive price point.

**Bottom Line for Developers**

If you need a fast, affordable model for production workloads, GPT-4o mini is worth testing immediately. It's ideal for classification, extraction, and high-volume chat applications."""
    return paper


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "1"
    return mock_response


@pytest.fixture
def mock_openai_summary_response():
    """Mock OpenAI API response for summarization."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "OpenAI released GPT-4o mini, a cost-effective model with 128K context and function calling."
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
