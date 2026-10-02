"""Unit tests for blog fetcher module."""

from datetime import datetime, timedelta, timezone
import socket
from unittest.mock import patch, MagicMock

import pytest

from src.constants import BLOG_FEEDS
from src.constants import DIGEST_MAX_AGE_HOURS
from src.fetchers.blog_fetcher import (
    fetch_blog_posts,
    _fetch_single_feed,
    _is_noise,
    _is_tutorial,
)


class TestBlogFetcher:
    """Tests for blog fetcher."""

    def test_fetch_single_feed_success(self, mock_blog_feed):
        """Test successful single feed fetching."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = False
            mock_response.entries = mock_blog_feed["entries"]
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("OpenAI", "https://openai.com/blog/rss.xml", DIGEST_MAX_AGE_HOURS, 20)

            assert len(posts) == 1
            assert posts[0]["source"] == "OpenAI"
            assert posts[0]["type"] == "announcement"

    def test_fetch_single_feed_timeout(self):
        """Test single feed handles timeout gracefully."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_parse.side_effect = socket.timeout()

            posts = _fetch_single_feed("Test Blog", "https://test.com/rss", DIGEST_MAX_AGE_HOURS, 20)

            assert posts == []

    def test_fetch_blog_posts_aggregates_sources(self, mock_blog_feed):
        """Test that blog posts are aggregated from multiple sources."""
        with patch("src.fetchers.blog_fetcher._fetch_single_feed") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "title": "Test Post",
                    "summary": "Test description about new API launch",
                    "url": "https://test.com/post",
                    "source": "Test Blog",
                    "published": "2024-01-15T00:00:00",
                    "type": "announcement",
                }
            ]

            posts = fetch_blog_posts(max_results=5)

            # Should be called once per configured blog feed
            assert mock_fetch.call_count == len(BLOG_FEEDS)

    def test_fetch_single_feed_parse_error(self):
        """Test single feed handles parse errors gracefully."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = True
            mock_response.entries = []
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("Test Blog", "https://test.com/rss", DIGEST_MAX_AGE_HOURS, 20)

            assert posts == []

    def test_fetch_single_feed_respects_max(self, mock_blog_feed):
        """Test that single feed respects max_per_source limit."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = False
            # Create multiple entries
            mock_response.entries = mock_blog_feed["entries"] * 10
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("OpenAI", "https://openai.com/blog/rss.xml", DIGEST_MAX_AGE_HOURS, 2)

            assert len(posts) <= 2


class TestNoiseFilter:
    """_is_noise is deliberately NOT a topic test.

    Everything in BLOG_FEEDS is a lab's own blog, so requiring a topic keyword
    there dropped real launches: DeepMind's "Introducing SynthID Bio" and all
    five of Google Research's most recent posts, while "public beta" waved
    through an OpenStreetMap app. Only genuine noise is excluded now.
    """

    def test_lab_release_is_not_noise(self):
        post = {"title": "Introducing our new frontier model",
                "summary": "A reasoning model, now in the API"}
        assert _is_noise(post) is False

    @pytest.mark.parametrize("title", [
        "Introducing SynthID Bio",
        "Advancing Private AI Compute with secure, server-side memory",
        "Bypassing inference bottlenecks: Accelerating complex AI search",
        "Automating coherent long-form video generation",
        "How Diffusion Controller unifies and simplifies AI image generation",
    ])
    def test_real_lab_posts_with_no_topic_keyword_survive(self, title):
        """These were all dropped in production for naming no model family."""
        assert _is_noise({"title": title, "summary": ""}) is False

    def test_hiring_is_noise(self):
        post = {"title": "We are hiring across the company",
                "summary": "Open roles on every team"}
        assert _is_noise(post) is True

    def test_funding_round_is_noise(self):
        """A lab raising money is not a development, however big the number."""
        post = {"title": "Mistral raises EUR 3B", "summary": "Series B led by investors"}
        assert _is_noise(post) is True

    def test_tutorial_is_noise(self):
        assert _is_noise({"title": "How to build a RAG pipeline", "summary": ""}) is True

    def test_off_domain_corporate_content_is_noise(self):
        """NVIDIA's feed is the whole company blog, not an AI-lab feed."""
        assert _is_noise({"title": "Fall Into 25 New Games on GeForce NOW", "summary": ""}) is True


class TestRecencyWindow:
    """Entries are selected by date, not by position in the feed."""

    def _feed_with(self, hours_old: int):
        when = datetime.now(timezone.utc) - timedelta(hours=hours_old)
        entry = {
            "title": "A frontier model lands",
            "summary": "Details inside",
            "link": "https://lab.example/post",
            "published": when.isoformat(),
            "published_parsed": when.timetuple()[:9],
        }
        resp = MagicMock()
        resp.bozo = False
        resp.entries = [entry]
        return resp

    def test_entry_inside_the_window_is_kept(self):
        with patch("src.fetchers.blog_fetcher.feedparser.parse", return_value=self._feed_with(5)):
            assert len(_fetch_single_feed("Lab", "https://x/rss", 72, 20)) == 1

    def test_entry_outside_the_window_is_dropped(self):
        with patch("src.fetchers.blog_fetcher.feedparser.parse", return_value=self._feed_with(200)):
            assert _fetch_single_feed("Lab", "https://x/rss", 72, 20) == []

    def test_position_no_longer_caps_what_is_considered(self):
        """The old code looked at entries[:5] whatever the feed held."""
        when = datetime.now(timezone.utc) - timedelta(hours=1)
        entries = [{
            "title": f"Release {i}", "summary": "", "link": f"https://lab.example/{i}",
            "published": when.isoformat(), "published_parsed": when.timetuple()[:9],
        } for i in range(12)]
        resp = MagicMock(); resp.bozo = False; resp.entries = entries
        with patch("src.fetchers.blog_fetcher.feedparser.parse", return_value=resp):
            assert len(_fetch_single_feed("Lab", "https://x/rss", 72, 20)) == 12


class TestTutorialFilter:
    """Tests for excluding vendor how-tos from the candidate pool."""

    def test_blocks_the_real_winners(self):
        """Both items that actually won the daily pick were tutorials."""
        assert _is_tutorial("Preparing data for supervised fine-tuning Part 2: Advanced data strategies")
        assert _is_tutorial("Build agentic creative workflows with Amazon Quick and fal")

    @pytest.mark.parametrize("title", [
        "Gemini-3.5-Transcribe",
        "Gemini Omni 1.1 Flash",
        "Piloting the world's first double-blind AI evaluations",
        "The Hugging Face incident and the road ahead",
        "Qwen3.8-Flash-Next: A New Architecture, Towards Ultimate Cost Efficiency",
        "GSPO: Towards Scalable Reinforcement Learning for Language Models",
        "Introducing GPT-5.6 in the API",
        "anthropic-sdk-python v1.2.0 released",
    ])
    def test_real_lab_news_survives(self, title):
        """False positives here would silently drop genuine launches."""
        assert not _is_tutorial(title)

    def test_matches_title_only_not_summary(self):
        """A launch post whose body says 'how to' must not be dropped."""
        post = {
            "title": "Introducing our new frontier model",
            "summary": "We show how to call the new developer api endpoint.",
        }
        assert _is_noise(post) is False
