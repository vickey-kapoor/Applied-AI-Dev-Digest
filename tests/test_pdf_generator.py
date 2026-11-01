"""Unit tests for PDF generator module."""

import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.pdf_generator import (
    ANNOUNCEMENT_CHARS,
    _sanitize_text_for_pdf,
    _truncate,
    default_output_dir,
    generate_digest_pdf,
)


@pytest.fixture
def pdf_output_dir():
    """Provide a repo-local writable directory for PDF test output."""
    output_dir = Path.cwd() / ".test-pdfs" / str(uuid.uuid4())
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield str(output_dir)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


class TestSanitizeTextForPdf:
    """Tests for PDF text sanitization."""

    def test_empty_text(self):
        """Test sanitization of empty text."""
        assert _sanitize_text_for_pdf("") == ""
        assert _sanitize_text_for_pdf(None) == ""

    def test_plain_text(self):
        """Test that plain ASCII text passes through."""
        text = "This is plain ASCII text."
        assert _sanitize_text_for_pdf(text) == text

    def test_smart_quotes_replacement(self):
        """Test that smart quotes are replaced with ASCII."""
        text = "He said \u201cHello\u201d and \u2018Hi\u2019"
        result = _sanitize_text_for_pdf(text)
        assert '"' in result
        assert "'" in result
        assert "\u201c" not in result
        assert "\u2018" not in result

    def test_dash_replacement(self):
        """Test that em/en dashes are replaced."""
        text = "Range: 1\u20132 and also\u2014this"
        result = _sanitize_text_for_pdf(text)
        assert "-" in result
        assert "\u2013" not in result
        assert "\u2014" not in result

    def test_ellipsis_replacement(self):
        """Test that ellipsis character is replaced."""
        text = "And so on\u2026"
        result = _sanitize_text_for_pdf(text)
        assert "..." in result
        assert "\u2026" not in result

    def test_non_breaking_space(self):
        """Test that non-breaking spaces are replaced."""
        text = "Word\u00a0Word"
        result = _sanitize_text_for_pdf(text)
        assert " " in result
        assert "\u00a0" not in result


class TestDefaultOutputDir:
    """Where a brief goes when the caller names no directory."""

    def test_defaults_outside_the_repository(self, monkeypatch):
        """Not the checkout: briefs are not kept in the repo or the working tree."""
        monkeypatch.delenv("DIGEST_REPORTS_DIR", raising=False)

        default = Path(default_output_dir()).resolve()

        assert default == Path(tempfile.gettempdir()).resolve() / "ai-dev-digest-reports"
        assert Path.cwd().resolve() not in default.parents

    def test_env_var_overrides(self, monkeypatch, tmp_path):
        """A local run can point the brief somewhere findable."""
        monkeypatch.setenv("DIGEST_REPORTS_DIR", str(tmp_path / "briefs"))

        assert default_output_dir() == str(tmp_path / "briefs")

    def test_blank_env_var_falls_back(self, monkeypatch):
        """An empty value is not a directory name."""
        monkeypatch.setenv("DIGEST_REPORTS_DIR", "   ")

        assert default_output_dir() == str(
            Path(tempfile.gettempdir()) / "ai-dev-digest-reports"
        )


class TestGenerateDigestPdf:
    """Tests for single digest PDF generation."""

    def test_generate_pdf_writes_outside_the_repo_by_default(
        self, sample_paper_with_detailed_summary, monkeypatch, tmp_path
    ):
        """With no output_dir, the brief lands in the scratch directory."""
        monkeypatch.setenv("DIGEST_REPORTS_DIR", str(tmp_path / "scratch"))

        pdf_path = Path(generate_digest_pdf(sample_paper_with_detailed_summary))

        assert pdf_path.exists()
        assert (tmp_path / "scratch").resolve() in pdf_path.resolve().parents

    def test_generate_pdf_creates_file(self, sample_paper_with_detailed_summary, pdf_output_dir):
        """Test that PDF file is created."""
        pdf_path = generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")

    def test_generate_pdf_uses_iso_date_folder_under_the_year(
        self, sample_paper_with_detailed_summary, pdf_output_dir
    ):
        """The PDF lands in <output_dir>/YYYY/YYYY-MM-DD/, today's date in UTC."""
        pdf_path = generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

        today = datetime.now(timezone.utc)
        day_dir = Path(pdf_path).parent
        assert day_dir.name == today.strftime("%Y-%m-%d")
        assert day_dir.parent.name == today.strftime("%Y")

    def test_generate_pdf_safe_filename(self, sample_paper, pdf_output_dir):
        """Test that filename is sanitized."""
        paper = sample_paper.copy()
        paper["title"] = "Research: A/B Test <script>alert(1)</script>"
        paper["summary"] = "Test summary"

        pdf_path = generate_digest_pdf(paper, output_dir=pdf_output_dir)

        # Filename should not contain unsafe characters
        filename = os.path.basename(pdf_path)
        assert "/" not in filename
        assert "<" not in filename
        assert ">" not in filename

    def test_generate_pdf_with_summary(self, sample_paper_with_summary, pdf_output_dir):
        """Test PDF generation with short summary (fallback)."""
        pdf_path = generate_digest_pdf(sample_paper_with_summary, output_dir=pdf_output_dir)

        assert os.path.exists(pdf_path)

    def test_generate_pdf_with_detailed_summary(self, sample_paper_with_detailed_summary, pdf_output_dir):
        """Test PDF generation with detailed summary (preferred)."""
        pdf_path = generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

        assert os.path.exists(pdf_path)
        # File should have some content (more than just headers)
        assert os.path.getsize(pdf_path) > 1000

    def test_generate_pdf_handles_special_characters(self, sample_paper, pdf_output_dir):
        """Test PDF handles special characters gracefully."""
        paper = sample_paper.copy()
        paper["title"] = "Research with \u201csmart quotes\u201d"
        paper["description"] = "Abstract with \u2014 em dash and \u2026 ellipsis"
        paper["summary"] = "Summary with \u00a0non-breaking space"

        # Should not raise exception
        pdf_path = generate_digest_pdf(paper, output_dir=pdf_output_dir)
        assert os.path.exists(pdf_path)


class _Recorder:
    """A stand-in for DigestPDF that records what was written, and where.

    The PDF's own rendering is fpdf2's business; what this file needs to pin
    down is the text the generator hands it and the font it asks for.
    """

    def __init__(self):
        self.writes: list[tuple[str, str]] = []
        self._style = ""

    def set_font(self, _family, style="", _size=None):
        self._style = style

    def cell(self, _w, _h, text="", **_kwargs):
        self.writes.append((self._style, text))

    def multi_cell(self, _w, _h, text="", **_kwargs):
        self.writes.append((self._style, text))

    def get_y(self):
        return 0.0

    def output(self, _path):
        Path(_path).write_bytes(b"%PDF-1.4 recorded")

    def __getattr__(self, _name):
        # ln, line, set_text_color, set_draw_color, add_page, set_y: position
        # and colour, none of which this file asserts on.
        return lambda *args, **kwargs: None

    @property
    def text(self) -> str:
        return "\n".join(text for _, text in self.writes)


@pytest.fixture
def recorded(monkeypatch):
    """Generate a PDF against the recorder and hand back what was written."""
    recorder = _Recorder()
    monkeypatch.setattr("src.pdf_generator.DigestPDF", lambda: recorder)
    return recorder


class TestTruncate:
    def test_short_text_is_untouched(self):
        assert _truncate("Three words here", 100) == "Three words here"

    def test_long_text_is_cut_on_a_word_boundary(self):
        result = _truncate("alpha beta gamma delta", 14)
        assert result == "alpha beta..."

    def test_empty_text(self):
        assert _truncate("", 10) == ""
        assert _truncate(None, 10) == ""


class TestBriefRendering:
    """The brief arrives as Markdown, because preview.py prints it to a terminal."""

    def test_section_headings_do_not_print_their_asterisks(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)
        assert "**" not in recorded.text

    def test_section_headings_are_written_in_bold(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)
        assert ("B", "What shipped") in recorded.writes
        assert ("B", "Caveats") in recorded.writes

    def test_section_bodies_are_not_bold(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        generate_digest_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)
        bodies = [
            style for style, text in recorded.writes
            if text.startswith("Generally available in the API today")
        ]
        assert bodies == [""]


class TestSourceLine:
    def test_the_source_is_named_once(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        """It used to be printed twice, as "From: X" and then "Source: X"."""
        item = {**sample_paper_with_detailed_summary, "source": "Mistral AI"}
        generate_digest_pdf(item, output_dir=pdf_output_dir)
        assert recorded.text.count("Mistral AI") == 1


class TestAnnouncementSection:
    def test_it_shows_the_announcement_not_the_brief_again(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        item = {
            **sample_paper_with_detailed_summary,
            "article_text": "The announcement's own opening paragraph.",
        }
        generate_digest_pdf(item, output_dir=pdf_output_dir)
        assert "The announcement's own opening paragraph." in recorded.text
        # The brief's own text appears once, in the brief — not again below it.
        assert recorded.text.count("128K context with function calling") == 1

    def test_a_long_announcement_is_trimmed(
        self, sample_paper_with_detailed_summary, pdf_output_dir, recorded
    ):
        item = {
            **sample_paper_with_detailed_summary,
            "article_text": "word " * 4000,
        }
        generate_digest_pdf(item, output_dir=pdf_output_dir)
        written = [text for _, text in recorded.writes if text.startswith("word word")]
        assert written and len(written[0]) <= ANNOUNCEMENT_CHARS + len("...")

    def test_without_a_brief_the_feed_blurb_is_still_shown(
        self, sample_paper_with_summary, pdf_output_dir, recorded
    ):
        """A summarizer failure leaves only the blurb, and printing it is not a repeat."""
        item = {k: v for k, v in sample_paper_with_summary.items() if k != "detailed_summary"}
        item.pop("article_text", None)
        generate_digest_pdf(item, output_dir=pdf_output_dir)
        assert "OpenAI released GPT-4o mini" in recorded.text
