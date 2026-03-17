"""Unit tests for PDF generator module."""

import os
import shutil
import uuid
from pathlib import Path

import pytest

from src.pdf_generator import (
    _sanitize_text_for_pdf,
    generate_research_pdf,
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


class TestGenerateResearchPdf:
    """Tests for single research PDF generation."""

    def test_generate_pdf_creates_file(self, sample_paper_with_detailed_summary, pdf_output_dir):
        """Test that PDF file is created."""
        pdf_path = generate_research_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")

    def test_generate_pdf_uses_date_folder(self, sample_paper_with_detailed_summary, pdf_output_dir):
        """Test that PDF is saved in date-formatted folder."""
        pdf_path = generate_research_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

        # Path should contain date folder (e.g., "15-Jan")
        path_parts = Path(pdf_path).parts
        assert any("-" in part and len(part) == 6 for part in path_parts)

    def test_generate_pdf_safe_filename(self, sample_paper, pdf_output_dir):
        """Test that filename is sanitized."""
        paper = sample_paper.copy()
        paper["title"] = "Research: A/B Test <script>alert(1)</script>"
        paper["summary"] = "Test summary"

        pdf_path = generate_research_pdf(paper, output_dir=pdf_output_dir)

        # Filename should not contain unsafe characters
        filename = os.path.basename(pdf_path)
        assert "/" not in filename
        assert "<" not in filename
        assert ">" not in filename

    def test_generate_pdf_with_summary(self, sample_paper_with_summary, pdf_output_dir):
        """Test PDF generation with short summary (fallback)."""
        pdf_path = generate_research_pdf(sample_paper_with_summary, output_dir=pdf_output_dir)

        assert os.path.exists(pdf_path)

    def test_generate_pdf_with_detailed_summary(self, sample_paper_with_detailed_summary, pdf_output_dir):
        """Test PDF generation with detailed summary (preferred)."""
        pdf_path = generate_research_pdf(sample_paper_with_detailed_summary, output_dir=pdf_output_dir)

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
        pdf_path = generate_research_pdf(paper, output_dir=pdf_output_dir)
        assert os.path.exists(pdf_path)
