"""Unit tests for Hugging Face daily papers fetcher."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.fetchers.huggingface_fetcher import fetch_huggingface_papers


def _make_entry(title="Test Paper", upvotes=50, hours_ago=2, paper_id="2404.12345"):
    """Build a mock HF daily paper entry."""
    published = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return {
        "paper": {
            "id": paper_id,
            "title": title,
            "summary": "A short summary of the paper.",
        },
        "numUpvotes": upvotes,
        "publishedAt": published,
    }


class TestUpvoteFilter:
    """Tests for upvote threshold filtering."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_keeps_papers_above_threshold(self, mock_urlopen):
        entries = [_make_entry(upvotes=50), _make_entry(title="Low", upvotes=3, paper_id="low")]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert len(result) == 1
        assert result[0]["title"] == "Test Paper"

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_filters_all_below_threshold(self, mock_urlopen):
        entries = [_make_entry(upvotes=5), _make_entry(upvotes=2, paper_id="low")]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert len(result) == 0


class TestRecencyFilter:
    """Tests for 24-hour window filtering."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_keeps_recent_papers(self, mock_urlopen):
        entries = [_make_entry(hours_ago=2)]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert len(result) == 1

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_filters_old_papers(self, mock_urlopen):
        entries = [_make_entry(hours_ago=48)]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert len(result) == 0


class TestEmptyAndMalformedResponses:
    """Tests for edge cases in API responses."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert result == []

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_malformed_response_not_list(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"error": "not found"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert result == []

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_malformed_entry_skipped(self, mock_urlopen):
        entries = [
            {"paper": None, "numUpvotes": 100, "publishedAt": "2024-01-01T00:00:00Z"},
            _make_entry(upvotes=30, paper_id="good"),
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert len(result) == 1
        assert result[0]["title"] == "Test Paper"

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_network_error_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection failed")

        result = fetch_huggingface_papers()
        assert result == []


class TestOutputFormat:
    """Tests for returned item structure."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_item_has_expected_fields(self, mock_urlopen):
        entries = [_make_entry()]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        item = result[0]
        assert item["source"] == "Hugging Face"
        assert item["type"] == "paper"
        assert "huggingface.co/papers/" in item["url"]
        assert "upvotes" in item
        assert "published" in item

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_sorted_by_upvotes_descending(self, mock_urlopen):
        entries = [
            _make_entry(title="Low", upvotes=30, paper_id="a"),
            _make_entry(title="High", upvotes=100, paper_id="b"),
            _make_entry(title="Mid", upvotes=60, paper_id="c"),
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(entries).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = fetch_huggingface_papers()
        assert result[0]["title"] == "High"
        assert result[1]["title"] == "Mid"
        assert result[2]["title"] == "Low"
