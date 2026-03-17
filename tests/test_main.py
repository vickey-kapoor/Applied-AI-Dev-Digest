"""Unit tests for the application entry point."""

from unittest.mock import Mock, patch

import pytest

import main


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

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_research_message")
    @patch("main.generate_research_pdf")
    @patch("main.summarize_research_bundle")
    @patch("main.export_papers")
    @patch("main.rank_research")
    @patch("main.fetch_ai_research")
    def test_main_uses_summary_bundle(
        self,
        mock_fetch_ai_research,
        mock_rank_research,
        mock_export_papers,
        mock_summarize_research_bundle,
        mock_generate_research_pdf,
        mock_format_research_message,
        mock_send_telegram_message,
        mock_export_digest,
        env_vars,
        monkeypatch,
    ):
        """The app should generate both summaries through the bundled call."""
        paper = {
            "title": "Test Paper",
            "description": "Test description",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/1234.5678",
            "authors": "Test Author",
        }
        enriched_paper = {
            **paper,
            "summary": "Short summary",
            "detailed_summary": "Detailed summary",
        }

        mock_fetch_ai_research.return_value = [paper]
        mock_rank_research.return_value = paper
        mock_export_papers.return_value = "paper-1"
        mock_summarize_research_bundle.return_value = enriched_paper
        mock_generate_research_pdf.return_value = "reports/13-Mar/test.pdf"
        mock_format_research_message.return_value = "formatted"
        monkeypatch.setenv("GITHUB_RUN_ID", "run-123")

        main.main()

        mock_summarize_research_bundle.assert_called_once_with(paper, "test_openai_key")
        mock_send_telegram_message.assert_called_once_with("test_bot_token", "12345", "formatted")
        mock_export_digest.assert_called_once()

    @patch("main.send_telegram_message")
    @patch("main.format_research_message")
    @patch("main.generate_research_pdf")
    @patch("main.summarize_research_bundle")
    @patch("main.export_digest")
    @patch("main.export_papers")
    @patch("main.rank_research")
    @patch("main.fetch_ai_research")
    def test_main_exits_when_telegram_send_fails(
        self,
        mock_fetch_ai_research,
        mock_rank_research,
        mock_export_papers,
        mock_export_digest,
        mock_summarize_research_bundle,
        mock_generate_research_pdf,
        mock_format_research_message,
        mock_send_telegram_message,
        env_vars,
    ):
        """The app should exit non-zero if the digest cannot be sent."""
        paper = {
            "title": "Test Paper",
            "description": "Test description",
            "source": "arXiv",
            "url": "https://arxiv.org/abs/1234.5678",
            "authors": "Test Author",
        }

        mock_fetch_ai_research.return_value = [paper]
        mock_rank_research.return_value = paper
        mock_export_papers.return_value = "paper-1"
        mock_summarize_research_bundle.return_value = paper
        mock_generate_research_pdf.return_value = "reports/13-Mar/test.pdf"
        mock_format_research_message.return_value = "formatted"
        mock_send_telegram_message.side_effect = RuntimeError("send failed")

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 1
