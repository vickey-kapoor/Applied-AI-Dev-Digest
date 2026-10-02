"""Unit tests for Telegram sender module."""

import pytest
from unittest.mock import Mock, patch

from src.telegram_sender import (
    _validate_url,
    _truncate,
    _truncate_message,
    _escape_markdown,
    HEADLINE_LIMIT,
    format_digest_message,
    send_telegram_message,
)


class TestUrlValidation:
    """Tests for URL validation."""

    def test_valid_https_url(self):
        url = "https://arxiv.org/abs/2401.12345"
        assert _validate_url(url) == url

    def test_valid_http_url(self):
        url = "http://example.com/paper"
        assert _validate_url(url) == url

    def test_empty_url(self):
        assert _validate_url("") == ""
        assert _validate_url(None) == ""

    def test_invalid_scheme(self):
        assert _validate_url("ftp://example.com") == ""
        assert _validate_url("file:///etc/passwd") == ""

    def test_javascript_injection(self):
        assert _validate_url("javascript:alert(1)") == ""

    def test_data_url(self):
        assert _validate_url("data:text/html,<script>alert(1)</script>") == ""

    def test_xss_patterns(self):
        assert _validate_url("https://example.com/<script>alert(1)</script>") == ""
        assert _validate_url("https://example.com/onclick=alert(1)") == ""

    def test_whitespace_handling(self):
        url = "  https://arxiv.org/abs/2401.12345  "
        assert _validate_url(url) == url.strip()

    def test_missing_netloc(self):
        assert _validate_url("https:///path") == ""


class TestTruncate:
    """Tests for text truncation."""

    def test_short_text(self):
        text = "Short text"
        assert _truncate(text, 100) == text

    def test_exact_length(self):
        text = "a" * 50
        assert _truncate(text, 50) == text

    def test_truncation(self):
        text = "This is a long sentence that needs truncation"
        result = _truncate(text, 20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_word_boundary(self):
        text = "This is a test sentence"
        result = _truncate(text, 15)
        assert result == "This is a..."


class TestTruncateMessage:
    """Tests for Telegram message truncation."""

    def test_short_message_unchanged(self):
        message = "Hello world"
        assert _truncate_message(message) == message

    def test_long_message_truncated(self):
        message = "Line\n" * 2000  # Way over 4096
        result = _truncate_message(message)
        assert len(result) <= 4096
        assert result.endswith("...")

    def test_exact_limit_unchanged(self):
        message = "a" * 4096
        assert _truncate_message(message) == message

    def test_truncation_at_newline_boundary(self):
        # Build a message just over the limit
        message = "Short line\n" * 400  # 4400 chars
        result = _truncate_message(message)
        assert len(result) <= 4096
        assert result.endswith("...")


class TestEscapeMarkdown:
    """Tests for Telegram Markdown escaping."""

    def test_escapes_special_characters(self):
        text = "Paper_[v2] *draft*"
        result = _escape_markdown(text)
        assert result == "Paper\\_\\[v2\\] \\*draft\\*"


class TestFormatDigestMessage:
    """Tests for digest message formatting."""

    def test_basic_formatting(self, sample_paper_with_summary):
        message = format_digest_message(sample_paper_with_summary)
        assert sample_paper_with_summary["title"] in message
        assert "What shipped" in message
        assert "Capabilities" in message
        assert "Availability" in message
        assert "Why it matters" in message
        assert "Caveats" in message
        assert sample_paper_with_summary["source"] in message

    def test_empty_item(self):
        message = format_digest_message({})
        assert "No updates found today" in message

    def test_none_item(self):
        message = format_digest_message(None)
        assert "No updates found today" in message

    def test_url_validation_in_message(self, sample_paper_with_summary):
        paper = sample_paper_with_summary.copy()
        paper["url"] = "javascript:alert(1)"
        message = format_digest_message(paper)
        assert "javascript:" not in message

    def test_source_shown_in_message(self, sample_paper_with_summary):
        message = format_digest_message(sample_paper_with_summary)
        assert "OpenAI" in message

    def test_fallback_to_flat_summary(self, sample_paper):
        """Items without structured fields fall back to flat summary display."""
        paper = sample_paper.copy()
        paper["summary"] = "Flat summary text"
        message = format_digest_message(paper)
        assert "Flat summary text" in message

    def test_markdown_is_escaped_in_message(self, sample_paper):
        paper = sample_paper.copy()
        paper["title"] = "Paper_[v2]"
        paper["what_shipped"] = "Uses *special* syntax"
        paper["capabilities"] = "Technical details"
        message = format_digest_message(paper)
        assert "*Paper\\_\\[v2\\]*" in message
        assert "Uses \\*special\\* syntax" in message


class TestSendTelegramMessage:
    """Tests for Telegram message sending."""

    @patch("src.telegram_sender.requests.post")
    def test_send_message_success(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = send_telegram_message("test_token", "12345", "Test message")

        assert result is True
        mock_post.assert_called_once()

    @patch("src.telegram_sender.requests.post")
    def test_send_message_failure(self, mock_post):
        mock_post.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            send_telegram_message("test_token", "12345", "Test message")

    @patch("src.telegram_sender.requests.post")
    def test_send_message_truncates_long_message(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        long_message = "A" * 5000
        send_telegram_message("test_token", "12345", long_message)

        # Verify the message sent was truncated
        call_args = mock_post.call_args
        sent_message = call_args[1]["json"]["text"] if "json" in call_args[1] else call_args[0][1]["text"]
        assert len(sent_message) <= 4096


class TestHeadlines:
    """The pool holds ~20 candidates a day and only the top pick was shown.

    'Staying up to date' needs the sweep as well as the detail, so the rest
    arrive as one-line headlines under the brief.
    """

    def _top(self):
        return {
            "title": "Lab ships a model",
            "source": "OpenAI",
            "url": "https://openai.com/a",
            "what_shipped": "A model.",
            "release_type": "model",
        }

    def test_no_headlines_when_there_are_none(self):
        """A one-item day must not render an empty section header."""
        msg = format_digest_message(self._top())
        assert "Also today" not in msg

    def test_headlines_render_with_link_and_source(self):
        msg = format_digest_message(self._top(), also=[
            {"title": "vLLM 0.12 lands", "source": "Together AI", "url": "https://x.dev/v"},
        ])
        assert "*Also today*" in msg
        assert "[vLLM 0.12 lands](https://x.dev/v)" in msg
        assert "Together AI" in msg

    def test_headlines_are_capped(self):
        extras = [
            {"title": f"Item {i}", "source": "S", "url": f"https://x.dev/{i}"}
            for i in range(12)
        ]
        msg = format_digest_message(self._top(), also=extras)
        assert msg.count("•") == HEADLINE_LIMIT

    def test_headline_without_a_url_still_renders(self):
        msg = format_digest_message(self._top(), also=[{"title": "No link", "source": "S"}])
        assert "No link" in msg

    def test_headline_titles_are_escaped(self):
        """Unescaped markdown in a title would break the whole message."""
        msg = format_digest_message(self._top(), also=[
            {"title": "A *bold* claim_here", "source": "S", "url": "https://x.dev/1"},
        ])
        assert "\\*bold\\*" in msg

    def test_headlines_appear_on_the_flat_summary_fallback_too(self):
        """An item with no structured brief still takes the other headlines."""
        flat = {"title": "T", "source": "S", "url": "https://x.dev/t", "summary": "Plain."}
        msg = format_digest_message(flat, also=[
            {"title": "Second thing", "source": "S", "url": "https://x.dev/2"},
        ])
        assert "Second thing" in msg


class TestHeadlineNotes:
    """The ranker writes the headline line; the title is only a fallback."""

    def _top(self):
        return {"title": "Top", "source": "S", "url": "https://x.dev/t", "what_shipped": "W"}

    def test_note_replaces_the_bare_title(self):
        msg = format_digest_message(self._top(), also=[{
            "title": "vLLM v0.12 released",
            "headline_note": "vLLM 0.12: 2x throughput on MoE models",
            "source": "GitHub", "url": "https://x.dev/v",
        }])
        assert "2x throughput on MoE models" in msg
        assert "vLLM v0.12 released" not in msg

    def test_title_is_used_when_no_note_was_written(self):
        msg = format_digest_message(self._top(), also=[
            {"title": "Plain title", "source": "S", "url": "https://x.dev/p"},
        ])
        assert "Plain title" in msg

    def test_notes_are_escaped(self):
        msg = format_digest_message(self._top(), also=[{
            "title": "t", "headline_note": "Cuts cost 2*_fold_", "source": "S", "url": "https://x.dev/1",
        }])
        assert "2\\*" in msg
