"""Tests for weekly_digest.py."""

from unittest.mock import patch, MagicMock

import pytest

from weekly_digest import _deduplicate, _format_weekly_message, main


SAMPLE_PAPERS = [
    {
        "title": "Paper Alpha",
        "source": "Anthropic",
        "type": "paper",
        "topic_id": "alignment",
        "url": "https://example.com/alpha",
        "claim": "Models exhibit alignment-faking under monitoring.",
        "safety_relevance": "Updates threat model for training-time alignment.",
        "rigor": "preprint",
        "date": "2026-04-01",
    },
    {
        "title": "Paper Beta",
        "source": "Apollo Research",
        "type": "paper",
        "topic_id": "interpretability",
        "url": "https://example.com/beta",
        "claim": "New SAE training recipe improves feature recovery.",
        "safety_relevance": "Better interp tools for monitoring frontier behavior.",
        "rigor": "preprint",
        "date": "2026-04-02",
    },
    {
        "title": "Paper Gamma",
        "source": "Hacker News",
        "type": "discussion",
        "topic_id": None,
        "url": "https://example.com/gamma",
        "claim": "",
        "safety_relevance": "",
        "rigor": "",
        "date": "2026-04-03",
    },
]


class TestDeduplicate:
    def test_removes_exact_duplicates(self):
        papers = [{"title": "Same"}, {"title": "Same"}, {"title": "Different"}]
        result = _deduplicate(papers)
        assert len(result) == 2

    def test_case_insensitive(self):
        papers = [{"title": "Paper A"}, {"title": "paper a"}]
        result = _deduplicate(papers)
        assert len(result) == 1

    def test_preserves_order(self):
        papers = [{"title": "First"}, {"title": "Second"}, {"title": "First"}]
        result = _deduplicate(papers)
        assert result[0]["title"] == "First"
        assert result[1]["title"] == "Second"

    def test_empty_list(self):
        assert _deduplicate([]) == []


class TestFormatWeeklyMessage:
    def test_contains_header(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "Week in AI Safety" in msg

    def test_contains_all_titles(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "Paper Alpha" in msg
        assert "Paper Beta" in msg
        assert "Paper Gamma" in msg

    def test_numbers_entries(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "1\\." in msg
        assert "2\\." in msg
        assert "3\\." in msg

    def test_includes_source(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "Anthropic" in msg

    def test_includes_claim_when_present(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "alignment-faking" in msg

    def test_includes_rigor_when_present(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "preprint" in msg

    def test_includes_footer(self):
        msg = _format_weekly_message(SAMPLE_PAPERS)
        assert "See you next week" in msg


class TestMain:
    @patch("weekly_digest.kv_delete")
    @patch("weekly_digest.send_telegram_message")
    @patch("weekly_digest.kv_get_list")
    def test_sends_digest_when_enough_papers(self, mock_get, mock_send, mock_del, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        mock_get.return_value = SAMPLE_PAPERS

        main()

        mock_send.assert_called_once()
        msg = mock_send.call_args[0][2]
        assert "Week in AI Safety" in msg
        mock_del.assert_called_once_with("digest:weekly")

    @patch("weekly_digest.kv_delete")
    @patch("weekly_digest.send_telegram_message")
    @patch("weekly_digest.kv_get_list")
    def test_skips_when_too_few_papers(self, mock_get, mock_send, mock_del, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        mock_get.return_value = [SAMPLE_PAPERS[0], SAMPLE_PAPERS[1]]

        main()

        mock_send.assert_not_called()
        mock_del.assert_not_called()

    @patch("weekly_digest.kv_delete")
    @patch("weekly_digest.send_telegram_message")
    @patch("weekly_digest.kv_get_list")
    def test_deduplicates_before_sending(self, mock_get, mock_send, mock_del, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        papers = SAMPLE_PAPERS + [{"title": "Paper Alpha", "source": "Dupe"}]
        mock_get.return_value = papers

        main()

        mock_send.assert_called_once()
        msg = mock_send.call_args[0][2]
        assert msg.count("Paper Alpha") == 1
