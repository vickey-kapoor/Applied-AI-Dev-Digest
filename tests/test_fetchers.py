"""Unit tests for blog fetcher module."""

import socket
from unittest.mock import patch, MagicMock

import pytest

from src.fetchers.blog_fetcher import fetch_blog_posts, _fetch_single_feed


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
            assert posts[0]["lab"] == "OpenAI"
            assert posts[0]["type"] == "product_update"

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
                    "description": "Test description about new API launch",
                    "source": "Test Blog",
                    "lab": "Test Blog",
                    "url": "https://test.com/post",
                    "published_at": "2024-01-15T00:00:00",
                    "type": "product_update",
                    "authors": "Test Blog",
                    "topics": [],
                }
            ]

            posts = fetch_blog_posts(max_results=5)

            # Should be called for each blog feed (4 Tier 1 labs)
            assert mock_fetch.call_count == 4  # OpenAI, Anthropic, Google DeepMind, Meta AI

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
