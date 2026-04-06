"""Unit tests for blog fetcher module."""

import socket
from unittest.mock import patch, MagicMock

import pytest

from src.fetchers.blog_fetcher import fetch_blog_posts, _fetch_single_feed, _is_dev_relevant


class TestBlogFetcher:
    """Tests for blog fetcher."""

    def test_fetch_single_feed_success(self, mock_blog_feed):
        """Test successful single feed fetching."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = False
            mock_response.entries = mock_blog_feed["entries"]
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("OpenAI", "https://openai.com/blog/rss.xml", 5)

            assert len(posts) == 1
            assert posts[0]["source"] == "OpenAI"
            assert posts[0]["type"] == "announcement"

    def test_fetch_single_feed_timeout(self):
        """Test single feed handles timeout gracefully."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_parse.side_effect = socket.timeout()

            posts = _fetch_single_feed("Test Blog", "https://test.com/rss", 5)

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

            # Should be called for each blog feed (8 active feeds)
            assert mock_fetch.call_count == 8

    def test_fetch_single_feed_parse_error(self):
        """Test single feed handles parse errors gracefully."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = True
            mock_response.entries = []
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("Test Blog", "https://test.com/rss", 5)

            assert posts == []

    def test_fetch_single_feed_respects_max(self, mock_blog_feed):
        """Test that single feed respects max_per_source limit."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = False
            # Create multiple entries
            mock_response.entries = mock_blog_feed["entries"] * 10
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("OpenAI", "https://openai.com/blog/rss.xml", 2)

            assert len(posts) <= 2


class TestDevRelevanceFilter:
    """Tests for _is_dev_relevant filtering."""

    def test_is_dev_relevant_accepts_api_post(self):
        """Post with 'API' keyword in title is accepted."""
        post = {"title": "New API for developers", "summary": "Check it out"}
        assert _is_dev_relevant(post) is True

    def test_is_dev_relevant_rejects_partnership(self):
        """Post about partnership is rejected."""
        post = {"title": "We announce a partnership with Acme", "summary": "Exciting news"}
        assert _is_dev_relevant(post) is False

    def test_exclude_takes_precedence_over_include(self):
        """Post with both include and exclude keywords is rejected."""
        post = {"title": "API partnership announcement", "summary": "New API via partnership"}
        assert _is_dev_relevant(post) is False

    def test_no_keyword_match_rejected(self):
        """Generic post with no matching keywords is rejected."""
        post = {"title": "Our company vision for the future", "summary": "Thoughts on progress"}
        assert _is_dev_relevant(post) is False

    def test_filter_fallback_when_all_filtered(self, mock_blog_feed):
        """When all posts are filtered out, unfiltered list is returned."""
        with patch("src.fetchers.blog_fetcher.feedparser.parse") as mock_parse:
            mock_response = MagicMock()
            mock_response.bozo = False
            # Create entries that won't match any filter keywords
            entry = MagicMock()
            entry.get = lambda k, d="": {
                "title": "Our company culture",
                "summary": "A day in the life",
                "summary": "",
                "link": "https://test.com/post",
            }.get(k, d)
            entry.__contains__ = lambda self, k: k in ["title", "summary"]
            mock_response.entries = [entry]
            mock_parse.return_value = mock_response

            posts = _fetch_single_feed("TestBlog", "https://test.com/rss", 5)

            # Should return unfiltered posts as fallback
            assert len(posts) == 1
            assert posts[0]["title"] == "Our company culture"
