"""Unit tests for Telegram sender module."""

import pytest
from unittest.mock import Mock, patch

from src.telegram_sender import (
    _validate_url,
    _truncate,
    _truncate_message,
    _escape_markdown,
    format_research_message,
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


class TestFormatResearchMessage:
    """Tests for research message formatting."""

    def test_basic_formatting(self, sample_paper_with_summary):
        message = format_research_message(sample_paper_with_summary)
        assert sample_paper_with_summary["title"] in message
        assert "Why it matters" in message
        assert "What it is" in message
        assert sample_paper_with_summary["source"] in message

    def test_empty_research(self):
        message = format_research_message({})
        assert "No updates found today" in message

    def test_none_research(self):
        message = format_research_message(None)
        assert "No updates found today" in message

    def test_url_validation_in_message(self, sample_paper_with_summary):
        paper = sample_paper_with_summary.copy()
        paper["url"] = "javascript:alert(1)"
        message = format_research_message(paper)
        assert "javascript:" not in message

    def test_source_shown_in_message(self, sample_paper_with_summary):
        message = format_research_message(sample_paper_with_summary)
        assert "OpenAI" in message

    def test_fallback_to_flat_summary(self, sample_paper):
        """Items without structured fields fall back to flat summary display."""
        paper = sample_paper.copy()
        paper["summary"] = "Flat summary text"
        message = format_research_message(paper)
        assert "Flat summary text" in message

    def test_markdown_is_escaped_in_message(self, sample_paper):
        paper = sample_paper.copy()
        paper["title"] = "Paper_[v2]"
        paper["why_it_matters"] = "Uses *special* syntax"
        paper["what_it_is"] = "Technical details"
        message = format_research_message(paper)
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
