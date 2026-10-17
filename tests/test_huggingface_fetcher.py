"""Unit tests for Hugging Face daily papers fetcher."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.fetchers.huggingface_fetcher import fetch_huggingface_papers


def _make_entry(title="Test Paper", upvotes=50, hours_ago=2, paper_id="2404.12345"):
    """Build a mock HF daily paper entry in the shape the API returns.

    The upvote count is on the nested paper object and the daily-list
    timestamp is `submittedOnDailyAt`. `publishedAt` is the arXiv date, which
    is deliberately older here than the daily-list date: the fetcher must not
    measure recency against it, or every real response is filtered away.
    """
    listed = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    arxiv = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    return {
        "paper": {
            "id": paper_id,
            "title": title,
            "summary": "A short summary of the paper.",
            "upvotes": upvotes,
            "submittedOnDailyAt": listed,
            "publishedAt": arxiv,
        },
        "publishedAt": arxiv,
    }


def _mock_response(payload):
    """Build a urlopen context-manager mock returning payload as JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


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
    """The chosen day is the recency filter; this fetcher applies no window.

    `submittedOnDailyAt` is midnight UTC of the list's own date, so by
    mid-afternoon yesterday's list is already over 40 hours old by that
    measure. A window here would empty the source for most of every day.
    Age is bounded downstream by DIGEST_MAX_AGE_HOURS in fetch_all.
    """

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_keeps_recent_papers(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([_make_entry(hours_ago=2)])

        assert len(fetch_huggingface_papers()) == 1

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_keeps_a_list_dated_at_yesterday_midnight(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([_make_entry(hours_ago=41)])

        assert len(fetch_huggingface_papers()) == 1


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


class TestLiveResponseShape:
    """Regression tests for the response shape that made this source silent."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_reads_upvotes_from_nested_paper_object(self, mock_urlopen):
        """The live API carries no top-level numUpvotes at all."""
        entry = _make_entry(upvotes=663)
        assert "numUpvotes" not in entry
        mock_urlopen.return_value = _mock_response([entry])

        result = fetch_huggingface_papers()
        assert len(result) == 1
        assert result[0]["upvotes"] == 663

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_still_reads_legacy_top_level_upvotes(self, mock_urlopen):
        """An older shape with numUpvotes and no nested count still parses."""
        entry = _make_entry(upvotes=0)
        del entry["paper"]["upvotes"]
        entry["numUpvotes"] = 44
        mock_urlopen.return_value = _mock_response([entry])

        result = fetch_huggingface_papers()
        assert len(result) == 1
        assert result[0]["upvotes"] == 44

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_arxiv_date_does_not_age_out_a_freshly_listed_paper(self, mock_urlopen):
        """publishedAt runs days behind the daily list it appears on."""
        entry = _make_entry(hours_ago=2)
        entry["publishedAt"] = (
            datetime.now(timezone.utc) - timedelta(days=4)
        ).isoformat()
        mock_urlopen.return_value = _mock_response([entry])

        assert len(fetch_huggingface_papers()) == 1

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_published_field_is_the_daily_list_timestamp(self, mock_urlopen):
        """Downstream recency filtering reads this, so it must not be the arXiv date."""
        entry = _make_entry(hours_ago=5)
        mock_urlopen.return_value = _mock_response([entry])

        published = datetime.fromisoformat(fetch_huggingface_papers()[0]["published"])
        age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        assert age_hours < 6


class TestTodayNotYetPublished:
    """The daily list is empty until HF publishes the day's selection."""

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_falls_back_to_yesterday_when_today_is_empty(self, mock_urlopen):
        mock_urlopen.side_effect = [
            _mock_response([]),
            _mock_response([_make_entry(title="Yesterday's paper")]),
        ]

        result = fetch_huggingface_papers()
        assert len(result) == 1
        assert result[0]["title"] == "Yesterday's paper"
        assert mock_urlopen.call_count == 2

    @patch("src.fetchers.huggingface_fetcher.urllib.request.urlopen")
    def test_does_not_refetch_when_today_has_papers(self, mock_urlopen):
        mock_urlopen.side_effect = [_mock_response([_make_entry()])]

        assert len(fetch_huggingface_papers()) == 1
        assert mock_urlopen.call_count == 1
