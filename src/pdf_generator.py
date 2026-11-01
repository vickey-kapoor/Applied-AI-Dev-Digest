"""Generate PDF briefs for AI lab developments."""

import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF


def _sanitize_text_for_pdf(text: str) -> str:
    """
    Sanitize text for PDF output.

    Removes or replaces characters that might cause issues.
    """
    if not text:
        return ""

    # Replace common problematic characters
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2026': '...',  # Ellipsis
        '\u00a0': ' ',  # Non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove other non-ASCII characters that might cause issues
    text = text.encode('latin-1', errors='replace').decode('latin-1')

    return text


# How much of the announcement's own text the reference section carries. The
# fetcher's cap is 12,000 characters, which is a page and a half of small
# italics under a brief that already said what matters.
ANNOUNCEMENT_CHARS = 3000

# A brief section heading as the summarizer writes it: "**What shipped**" on a
# line of its own. The PDF renders these as bold headings rather than printing
# the asterisks, which is what it did before.
_BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*$")


def _truncate(text: str, max_len: int) -> str:
    """Trim to max_len on a word boundary, with an ellipsis when trimmed."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def _write_brief(pdf: FPDF, summary: str) -> None:
    """Render the structured brief, its "**Label**" lines as bold headings.

    The summarizer builds `detailed_summary` as Markdown because preview.py
    prints it to a terminal. The PDF used to pass that string straight to
    multi_cell, so every report showed literal asterisks around every heading.
    """
    for block in summary.split("\n"):
        line = block.strip()
        if not line:
            pdf.ln(3)
            continue
        heading = _BOLD_LINE.match(line)
        if heading:
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, heading.group(1), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")


class DigestPDF(FPDF):
    """Custom PDF class for lab-development briefs."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Add header to each page."""
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, "Daily AI Dev Digest", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, datetime.now(timezone.utc).strftime("%A, %B %d, %Y"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def default_output_dir() -> str:
    """Where a run writes its PDF when the caller names no directory.

    Briefs are no longer kept: nothing reads them back. The Telegram message is
    built from the item itself and the dashboard reads data/*.json, so a PDF
    committed to the repository was 205 files of write-only history. They now
    land in a scratch directory outside the working tree, which keeps the brief
    available for the run that made it without adding it to git or leaving it
    in the checkout.

    DIGEST_REPORTS_DIR overrides it, for running locally and wanting the file
    somewhere findable.
    """
    override = os.getenv("DIGEST_REPORTS_DIR", "").strip()
    if override:
        return override
    return str(Path(tempfile.gettempdir()) / "ai-dev-digest-reports")


def generate_digest_pdf(item: dict, output_dir: str = None) -> str:
    """
    Generate a PDF brief for an AI lab development.

    Args:
        item: Item dictionary with title, source, description, summary, url
        output_dir: Base directory for saving reports. Defaults to a scratch
            directory outside the repository (see default_output_dir) — the
            brief is not a stored artifact.

    Returns:
        Path to the generated PDF file
    """
    if output_dir is None:
        output_dir = default_output_dir()
    # Date-partitioned folder, ISO 8601 so it sorts chronologically and names
    # the year: "reports/2026/2026-03-06". The old layout was "%d-%b"
    # ("06-Mar"), which sorted by day-of-month and merged the same calendar day
    # from different years into one folder.
    now = datetime.now(timezone.utc)
    full_output_dir = Path(output_dir) / now.strftime("%Y") / now.strftime("%Y-%m-%d")
    full_output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize all text inputs
    title = _sanitize_text_for_pdf(item.get("title", "Today's AI Lab Development"))
    source = _sanitize_text_for_pdf(item.get("source", "Unknown"))
    # Use detailed_summary for PDF if available, fallback to short summary
    summary = _sanitize_text_for_pdf(
        item.get("detailed_summary", "") or item.get("summary", "")
    )
    # The announcement's own words. This used to read item["summary"], which
    # after summarization is the model's what_shipped + capabilities text — so
    # the section headed "Full Announcement Details" reprinted, verbatim, the
    # first two sections of the brief above it. The fetched page text is what
    # the heading has always claimed to show.
    # When there is no brief, the feed blurb is all there is and printing it
    # here is not a repeat.
    announcement = (item.get("article_text") or "").strip()
    if not announcement and not item.get("detailed_summary"):
        announcement = item.get("summary", "")
    description = _sanitize_text_for_pdf(_truncate(announcement, ANNOUNCEMENT_CHARS))
    url = item.get("url", "")

    # Create PDF
    pdf = DigestPDF()
    pdf.add_page()

    # Title section
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 60, 120)
    pdf.multi_cell(0, 12, title, align="C")
    pdf.ln(5)

    # Publishing lab. One line, not two: this and the badge below it both read
    # item["source"], so every report printed the same name twice.
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Source: {source}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Divider line
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    # Main section - the structured lab-release brief
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(50, 100, 50)
    pdf.cell(0, 10, "The Brief", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Structured brief body - use readable font size
    if summary:
        pdf.set_text_color(40, 40, 40)
        _write_brief(pdf, summary)
        pdf.ln(10)

    # Divider line
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    # Original announcement text (optional) - smaller, for reference
    if description:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "Full Announcement Details", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, description)
        pdf.ln(10)

    # Link section
    if url:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, "Want to learn more?", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 6, url, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

    # Friendly closing
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7, "This digest tracks the latest developments from the frontier AI labs - model releases, product and API launches, research reports, and capability results - as they ship.")

    # Generate filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title[:50])
    safe_title = safe_title.strip().replace(" ", "_")
    filename = f"{safe_title}.pdf"
    filepath = full_output_dir / filename

    # Save PDF
    pdf.output(str(filepath))

    return str(filepath)
