"""Unit tests for fetcher module (aggregation and deduplication)."""

import pytest
from unittest.mock import patch, MagicMock

from src.fetcher import (
    fetch_all,
    _deduplicate_by_url,
)


class TestDeduplicationByUrl:
    """Tests for URL-based deduplication."""

    def test_empty_list(self):
        assert _deduplicate_by_url([]) == []

    def test_no_duplicates(self):
        items = [
            {"url": "https://a.com", "title": "A"},
            {"url": "https://b.com", "title": "B"},
        ]
        assert len(_deduplicate_by_url(items)) == 2

    def test_removes_url_duplicates(self):
        items = [
            {"url": "https://a.com", "title": "First"},
            {"url": "https://a.com", "title": "Duplicate"},
        ]
        result = _deduplicate_by_url(items)
        assert len(result) == 1
        assert result[0]["title"] == "First"

    def test_keeps_items_with_different_urls(self):
        items = [
            {"url": "https://a.com", "title": "A"},
            {"url": "https://b.com", "title": "B"},
        ]
        assert len(_deduplicate_by_url(items)) == 2

    def test_items_without_url_kept(self):
        items = [
            {"title": "No URL"},
            {"url": "https://a.com", "title": "With URL"},
        ]
        assert len(_deduplicate_by_url(items)) == 2


class TestFetchAll:
    """Tests for the main fetch_all function."""

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_aggregates_blog_sources(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.return_value = [
            {"title": "OpenAI Update", "url": "https://a.com", "published": "2024-07-18"},
            {"title": "Anthropic Update", "url": "https://b.com", "published": "2024-07-17"},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 2

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases")
    @patch("src.fetcher.fetch_blog_posts")
    def test_aggregates_all_sources(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.return_value = [
            {"title": "Blog Post", "url": "https://a.com", "published": "2024-07-18"},
        ]
        mock_gh.return_value = [
            {"title": "transformers v4.40", "url": "https://github.com/x", "published": "2024-07-18"},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 2

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_handles_source_failure(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.side_effect = Exception("API Error")
        result = fetch_all(max_results=10)
        assert len(result) == 0

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_deduplicates_by_url(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.return_value = [
            {"title": "Same URL A", "url": "https://same.com", "published": "2024-07-18"},
            {"title": "Same URL B", "url": "https://same.com", "published": "2024-07-17"},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 1

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_respects_max_results(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.return_value = [
            {"title": f"Post {i}", "url": f"https://a.com/{i}", "published": f"2024-07-{18-i:02d}"}
            for i in range(10)
        ]
        result = fetch_all(max_results=3)
        assert len(result) == 3

    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_sorts_by_date(self, mock_blogs, mock_gh, mock_hn):
        mock_blogs.return_value = [
            {"title": "Old", "url": "https://a.com", "published": "2024-01-01"},
            {"title": "New", "url": "https://b.com", "published": "2024-07-18"},
        ]
        result = fetch_all(max_results=10)
        assert result[0]["title"] == "New"
        assert result[1]["title"] == "Old"
