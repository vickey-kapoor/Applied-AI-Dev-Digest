"""Shared pytest fixtures for AI Dev Digest tests."""

from datetime import datetime, timedelta, timezone

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
    """Sample item with a generated structured lab-release brief."""
    paper = sample_paper.copy()
    paper["what_shipped"] = "OpenAI released GPT-4o mini, a smaller GPT-4-class model, in the API."
    paper["capabilities"] = "128K context with function calling and JSON mode. Benchmarks are reported close to GPT-4o on coding and reasoning."
    paper["availability"] = "Generally available in the API today at $0.15 per 1M input tokens."
    paper["why_it_matters"] = "Drops the price floor for GPT-4-class quality, making high-volume classification and extraction workloads viable."
    paper["caveats"] = "Benchmark numbers are self-reported and the announcement gives no independent evaluation."
    paper["release_type"] = "model"
    paper["summary"] = "OpenAI released GPT-4o mini, a smaller GPT-4-class model, in the API. 128K context with function calling and JSON mode."
    return paper


@pytest.fixture
def sample_paper_with_detailed_summary(sample_paper_with_summary):
    """Sample item with detailed summary for PDF."""
    paper = sample_paper_with_summary.copy()
    paper["detailed_summary"] = """**What shipped**
OpenAI released GPT-4o mini, a smaller GPT-4-class model, in the API.

**Capabilities**
128K context with function calling and JSON mode. Benchmarks are reported close to GPT-4o on coding and reasoning.

**Availability**
Generally available in the API today at $0.15 per 1M input tokens.

**Why it matters**
Drops the price floor for GPT-4-class quality, making high-volume classification and extraction workloads viable.

**Caveats**
Benchmark numbers are self-reported and the announcement gives no independent evaluation."""
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
    mock_response.choices[0].message.content = '{"what_shipped": "Test what shipped.", "capabilities": "Test capabilities.", "availability": "Test availability.", "why_it_matters": "Test why it matters.", "caveats": "Test caveats.", "release_type": "model"}'
    return mock_response


@pytest.fixture
def mock_blog_feed():
    """Mock blog RSS feed response.

    Dated relative to now: the blog fetcher selects entries by recency window,
    so a hardcoded date silently ages out of every window and the fixture
    quietly starts returning nothing.
    """
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    return {
        "bozo": False,
        "entries": [
            {
                "title": "Introducing GPT-4o mini API",
                "summary": "OpenAI launches a new affordable model for developers.",
                "link": "https://openai.com/blog/gpt-4o-mini",
                "published": recent.isoformat(),
                "published_parsed": recent.timetuple()[:9],
            }
        ],
    }


@pytest.fixture
def env_vars(monkeypatch):
    """Set up required environment variables for testing."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
