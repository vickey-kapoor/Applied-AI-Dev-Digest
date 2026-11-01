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
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    def test_main_uses_summary_bundle(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_rank_news_ranked,
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
        mock_summarize_release.return_value = enriched_paper
        mock_generate_digest_pdf.return_value = "reports/2026/2026-03-13/test.pdf"
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
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["api", "sdk", "model"])
    def test_main_exits_when_telegram_send_fails(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_rank_news_ranked,
        mock_export_digest,
        mock_summarize_release,
        mock_generate_digest_pdf,
        mock_format_digest_message,
        mock_send_telegram_message,
        env_vars,
    ):
        """A digest that cannot be sent fails the run, after recording it.

        This used to exit 0. The day was then marked as done by the workflow,
        so nothing retried and nothing was sent — a green run with no digest.
        The recording still happens first, so the day keeps the attempt.
        """
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
        mock_summarize_release.return_value = paper
        mock_generate_digest_pdf.return_value = "reports/2026/2026-03-13/test.pdf"
        mock_format_digest_message.return_value = "formatted"
        mock_send_telegram_message.side_effect = RuntimeError("send failed")

        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 1
        mock_send_telegram_message.assert_called_once()
        # Digest still recorded even on send failure, so the day is not lost
        # just because Telegram was unreachable.
        mock_export_digest.assert_called_once()
        assert mock_export_digest.call_args.kwargs["telegram_sent"] is False

    @patch("main.send_telegram_message")
    @patch("main.export_digest")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    @patch("main.fetch_all", return_value=[])
    def test_empty_day_is_recorded(
        self,
        mock_fetch_all,
        mock_get_active_keywords,
        mock_export_digest,
        mock_send_telegram_message,
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


class TestQuietDayNotice:
    """A day with nothing to send says so, instead of passing in silence.

    Three days in the 45 to 07-Oct-2026 sent nothing — the pool came back
    empty — and every one of them is a green run in the Actions tab. The only
    signal reaching anyone was the absence of a message, which reads exactly
    like a broken pipeline.
    """

    @patch("main.send_telegram_message")
    @patch("main.export_digest")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    @patch("main.fetch_all", return_value=[])
    def test_an_empty_pool_is_announced(
        self,
        mock_fetch_all,
        mock_get_active_keywords,
        mock_export_digest,
        mock_send,
        env_vars,
    ):
        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0
        mock_send.assert_called_once()
        assert "No digest today" in mock_send.call_args.args[2]

    @patch("main.send_telegram_message")
    @patch("main.export_digest")
    @patch("main.get_sent_top_paper_ids")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    def test_an_all_seen_day_is_announced(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_sent_ids,
        mock_export_digest,
        mock_send,
        env_vars,
    ):
        """Every candidate was already sent as a previous top pick."""
        paper = {
            "title": "Already sent",
            "url": "https://openai.com/blog/old",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        mock_fetch_all.return_value = [paper]
        mock_sent_ids.return_value = {main._paper_id_for_item(paper)}

        main.main()

        mock_send.assert_called_once()
        assert "already been sent" in mock_send.call_args.args[2]

    @patch("main.send_telegram_message")
    @patch("main.export_digest")
    @patch("main.rank_news_ranked", return_value=[])
    @patch("main.get_sent_top_paper_ids", return_value=set())
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    def test_a_rejected_pool_is_announced(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_sent_ids,
        mock_rank,
        mock_export_digest,
        mock_send,
        env_vars,
    ):
        """The ranker judged nothing worth sending."""
        mock_fetch_all.return_value = [
            {
                "title": "Thin release note",
                "url": "https://example.com/x",
                "source": "Somewhere",
                "published": "2024-07-18T00:00:00",
                "type": "release",
            }
        ]

        main.main()

        mock_send.assert_called_once()
        assert "worth sending" in mock_send.call_args.args[2]

    @patch("main.send_telegram_message", side_effect=RuntimeError("telegram down"))
    @patch("main.export_digest")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    @patch("main.fetch_all", return_value=[])
    def test_a_failed_notice_does_not_fail_the_run(
        self,
        mock_fetch_all,
        mock_get_active_keywords,
        mock_export_digest,
        mock_send,
        env_vars,
    ):
        """A quiet day is already the mild outcome; failing to announce it is
        not worth turning into a red run and a retry."""
        with pytest.raises(SystemExit) as exc_info:
            main.main()

        assert exc_info.value.code == 0

    @patch("main.send_telegram_message")
    @patch("main.format_digest_message", return_value="formatted")
    @patch("main.export_digest")
    @patch("main.generate_digest_pdf", return_value="reports/x.pdf")
    @patch("main.summarize_release")
    @patch("main.rank_news_ranked")
    @patch("main.get_sent_top_paper_ids", return_value=set())
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    def test_a_normal_day_sends_no_notice(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_sent_ids,
        mock_rank,
        mock_summarize,
        mock_pdf,
        mock_export_digest,
        mock_format,
        mock_send,
        env_vars,
    ):
        """The digest itself is the only message on a day that has one."""
        paper = {
            "title": "Something shipped",
            "url": "https://openai.com/blog/new",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        mock_fetch_all.return_value = [paper]
        mock_rank.return_value = [paper]
        mock_summarize.return_value = paper

        main.main()

        mock_send.assert_called_once()
        assert mock_send.call_args.args[2] == "formatted"


class TestRejectedPoolDoesNotCrash:
    """The ranker returning nothing is a quiet day, not a broken run.

    `rank_news_ranked` can legitimately return an empty list — it rejects a
    thin pool rather than padding the digest. Everything downstream of the
    ranker still ran, and the export below died on `None.get`. The
    exception was uncaught, so the workflow step failed and every later tick
    that day repeated it: a red run, no digest, and no explanation.
    """

    @patch("main.send_telegram_message")
    @patch("main.export_digest")
    @patch("main.rank_news_ranked", return_value=[])
    @patch("main.get_sent_top_paper_ids", return_value=set())
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["frontier model"])
    def test_the_run_completes(
        self,
        mock_get_active_keywords,
        mock_fetch_all,
        mock_sent_ids,
        mock_rank,
        mock_export_digest,
        mock_send,
        env_vars,
    ):
        mock_fetch_all.return_value = [
            {
                "title": "Thin release note",
                "url": "https://example.com/x",
                "source": "Somewhere",
                "published": "2024-07-18T00:00:00",
                "type": "release",
            }
        ]

        main.main()  # must not raise

        # The day is still recorded, so it reads as a quiet day rather than a
        # run that never fired.
        mock_export_digest.assert_called_once()
        assert mock_export_digest.call_args.kwargs["telegram_sent"] is False
        assert mock_export_digest.call_args.kwargs["top_paper_id"] is None


class TestCandidatesAreOpenedBeforeRanking:
    """The ranker judges on what it is shown, so it is shown the articles.

    Until this, only the winner's link was opened, and only after the verdict.
    The ranker saw feed summaries, which are not comparable across sources:
    the Hugging Face blog sends none, Google Research sends a category label.
    """

    @staticmethod
    def _candidates():
        return [
            {"title": "Welcome Beam", "summary": "", "url": "https://hf.co/blog/beam",
             "source": "Hugging Face Blog", "published": "2026-10-17T00:00:00+00:00"},
            {"title": "Other news", "summary": "blurb", "url": "https://lab.example/x",
             "source": "NVIDIA", "published": "2026-10-17T00:00:00+00:00"},
        ]

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release", side_effect=lambda item, key: item)
    @patch("main.fetch_article_text", return_value="fetched late")
    @patch("main.attach_article_text")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["api"])
    def test_the_ranker_receives_items_carrying_article_text(
        self, _keywords, mock_fetch_all, mock_rank, mock_attach,
        _fetch_late, _summarize, _pdf, _format, _send, _digest, env_vars,
    ):
        candidates = self._candidates()
        mock_fetch_all.return_value = candidates
        mock_attach.side_effect = lambda items: [
            {**item, "article_text": f"body of {item['title']}"} for item in items
        ]
        mock_rank.side_effect = lambda items, key: items

        main.main()

        ranked_input = mock_rank.call_args[0][0]
        assert [i["article_text"] for i in ranked_input] == [
            "body of Welcome Beam",
            "body of Other news",
        ]

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release", side_effect=lambda item, key: item)
    @patch("main.fetch_article_text", return_value="fetched late")
    @patch("main.attach_article_text")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["api"])
    def test_the_winner_is_not_opened_a_second_time(
        self, _keywords, mock_fetch_all, mock_rank, mock_attach,
        mock_fetch_late, _summarize, _pdf, _format, _send, _digest, env_vars,
    ):
        """summarize_release reads the same field the pre-ranking fetch filled."""
        candidates = self._candidates()
        mock_fetch_all.return_value = candidates
        mock_attach.side_effect = lambda items: [
            {**item, "article_text": "already have it"} for item in items
        ]
        mock_rank.side_effect = lambda items, key: items

        main.main()

        mock_fetch_late.assert_not_called()

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.summarize_release", side_effect=lambda item, key: item)
    @patch("main.fetch_article_text", return_value="fetched late")
    @patch("main.attach_article_text", side_effect=Exception("every host down"))
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.get_active_keywords", return_value=["api"])
    def test_a_failure_to_open_the_links_still_sends_a_digest(
        self, _keywords, mock_fetch_all, mock_rank, _attach,
        _fetch_late, _summarize, _pdf, _format, mock_send, _digest, env_vars,
    ):
        """Ranking on feed summaries is the old behaviour: worse, not broken."""
        mock_fetch_all.return_value = self._candidates()
        mock_rank.side_effect = lambda items, key: items

        main.main()

        mock_send.assert_called_once()
