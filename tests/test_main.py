"""Unit tests for the application entry point."""

from unittest.mock import Mock, patch

import pytest

import main
from src.constants import HISTORY_MAX_ENTRIES


class TestMain:
    """Tests for main orchestration."""

    def test_main_exits_when_env_vars_missing(self, monkeypatch):
        """The app should fail fast when required configuration is missing."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 1

    @patch("main.is_paused", return_value=True)
    def test_main_exits_early_when_paused(self, mock_paused):
        """The app should exit cleanly when digest is paused."""
        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release")
    @patch("main.export_papers")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    @patch("main.is_paused", return_value=False)
    def test_main_uses_summary_bundle(
        self,
        mock_paused,
        mock_get_active_keywords,
        mock_increment_stat,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_papers,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        mock_export_digest,
        env_vars,
        monkeypatch,
    ):
        """The app should generate both summaries through the bundled call."""
        paper = {
            "title": "Test Paper",
            "summary": "Test summary",
            "url": "https://openai.com/blog/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        enriched_paper = {
            **paper,
            "summary": "Short summary",
            "detailed_summary": "Detailed summary",
        }

        mock_fetch_all.return_value = [paper]
        mock_rank_news_ranked.return_value = [paper]
        mock_export_papers.return_value = "paper-1"
        mock_summarize_release.return_value = enriched_paper
        mock_generate_digest_pdf.return_value = "reports/13-Mar/test.pdf"
        mock_format_digest_message.return_value = "formatted"
        monkeypatch.setenv("GITHUB_RUN_ID", "run-123")

        main.main()

        mock_summarize_release.assert_called_once_with(paper, "test_openai_key")
        mock_send_telegram_message.assert_called_once_with("test_bot_token", "12345", "formatted")
        mock_export_digest.assert_called_once()

    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release")
    @patch("main.export_digest")
    @patch("main.export_papers")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    @patch("main.is_paused", return_value=False)
    def test_main_exits_when_telegram_send_fails(
        self,
        mock_paused,
        mock_get_active_keywords,
        mock_increment_stat,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_papers,
        mock_export_digest,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        env_vars,
    ):
        """The app should log error but continue if Telegram send fails."""
        paper = {
            "title": "Test Paper",
            "summary": "Test summary",
            "url": "https://openai.com/blog/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }

        mock_fetch_all.return_value = [paper]
        mock_rank_news_ranked.return_value = [paper]
        mock_export_papers.return_value = "paper-1"
        mock_summarize_release.return_value = paper
        mock_generate_digest_pdf.return_value = "reports/13-Mar/test.pdf"
        mock_format_digest_message.return_value = "formatted"
        mock_send_telegram_message.side_effect = RuntimeError("send failed")

        # Pipeline continues despite Telegram failure (no sys.exit)
        main.main()

        mock_send_telegram_message.assert_called_once()
        # Digest still exported even on send failure
        mock_export_digest.assert_called_once()

    @patch("main.export_digest")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    @patch("main.fetch_all", return_value=[])
    @patch("main.is_paused", return_value=False)
    def test_empty_day_is_recorded(
        self,
        mock_paused,
        mock_fetch_all,
        mock_get_active_keywords,
        mock_export_digest,
        env_vars,
        monkeypatch,
    ):
        """A day with no items writes a digest entry instead of exiting silently."""
        monkeypatch.setenv("GITHUB_RUN_ID", "run-456")

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0
        mock_export_digest.assert_called_once()
        kwargs = mock_export_digest.call_args.kwargs
        assert kwargs["papers_fetched"] == 0
        assert kwargs["top_paper_id"] is None
        assert kwargs["telegram_sent"] is False
        assert kwargs["workflow_run_id"] == "run-456"

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message", return_value="formatted")
    @patch("main.generate_digest_pdf", return_value="reports/x.pdf")
    @patch("main.summarize_release")
    @patch("main.export_papers", return_value="paper-1")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    @patch("main.is_paused", return_value=False)
    def test_summarized_item_is_what_gets_exported(
        self,
        mock_paused,
        mock_get_active_keywords,
        mock_increment_stat,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_papers,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        mock_export_digest,
        env_vars,
    ):
        """papers.json must receive the summarized item, not the raw original."""
        paper = {
            "title": "Test Paper",
            "summary": "Raw RSS description",
            "url": "https://openai.com/blog/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        enriched = {**paper, "summary": "Generated summary", "what_shipped": "OpenAI shipped X."}

        mock_fetch_all.return_value = [paper]
        mock_rank_news_ranked.return_value = [paper]
        mock_summarize_release.return_value = enriched

        main.main()

        exported_items, exported_top = mock_export_papers.call_args[0]
        assert exported_items == [enriched]
        assert exported_top is enriched
        assert exported_items[0]["what_shipped"] == "OpenAI shipped X."


class TestHistoryList:
    """The KV list behind the dashboard's History page.

    The Sunday roundup used to send and then clear this list every week. It
    was removed, so the append side is now the only thing bounding it — an
    unbounded list would grow by one entry a day and the History page reads
    the whole of it.
    """

    @patch("main.kv_trim_to_last")
    @patch("main.kv_append")
    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message", return_value="formatted")
    @patch("main.generate_digest_pdf", return_value="reports/13-Mar/test.pdf")
    @patch("main.summarize_release")
    @patch("main.export_papers", return_value="paper-1")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    @patch("main.is_paused", return_value=False)
    def test_the_append_is_followed_by_a_trim(
        self,
        mock_paused,
        mock_get_active_keywords,
        mock_increment_stat,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_papers,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        mock_export_digest,
        mock_kv_append,
        mock_kv_trim,
        env_vars,
    ):
        paper = {
            "title": "Test Paper",
            "summary": "Test summary",
            "url": "https://openai.com/blog/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        mock_fetch_all.return_value = [paper]
        mock_rank_news_ranked.return_value = [paper]
        mock_summarize_release.return_value = dict(paper)

        main.main()

        mock_kv_append.assert_called_once()
        assert mock_kv_append.call_args[0][0] == "digest:weekly"

        mock_kv_trim.assert_called_once_with("digest:weekly", HISTORY_MAX_ENTRIES)

    @patch("main.kv_trim_to_last")
    @patch("main.kv_append", side_effect=RuntimeError("KV not configured"))
    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message", return_value="formatted")
    @patch("main.generate_digest_pdf", return_value="reports/13-Mar/test.pdf")
    @patch("main.summarize_release")
    @patch("main.export_papers", return_value="paper-1")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    @patch("main.is_paused", return_value=False)
    def test_a_failed_append_does_not_stop_the_digest(
        self,
        mock_paused,
        mock_get_active_keywords,
        mock_increment_stat,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_papers,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        mock_export_digest,
        mock_kv_append,
        mock_kv_trim,
        env_vars,
    ):
        """KV is optional for the pipeline, so neither call may be fatal."""
        paper = {
            "title": "Test Paper",
            "summary": "Test summary",
            "url": "https://openai.com/blog/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        mock_fetch_all.return_value = [paper]
        mock_rank_news_ranked.return_value = [paper]
        mock_summarize_release.return_value = dict(paper)

        main.main()

        mock_kv_trim.assert_not_called()
        mock_send_telegram_message.assert_called_once()
