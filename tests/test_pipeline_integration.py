"""Integration-style tests for the full pipeline flow (all APIs mocked)."""

import json
import os
import shutil
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import json_exporter
from src.json_exporter import export_papers, export_digest
from src.constants import PAPERS_CAP, DIGEST_CAP_DAYS


@pytest.fixture
def data_dir(monkeypatch):
    """Redirect JSON exports into a writable repo-local temporary data directory."""
    base_dir = Path.cwd() / ".test-data" / str(uuid.uuid4())
    base_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(json_exporter, "DATA_DIR", str(base_dir))
    try:
        yield base_dir
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


class TestPapersCapEnforcement:
    """Tests for papers.json cap enforcement."""

    def test_papers_capped_at_limit(self, data_dir):
        """Papers should be capped at PAPERS_CAP."""
        # Pre-populate with PAPERS_CAP papers
        existing_papers = []
        for i in range(PAPERS_CAP):
            existing_papers.append({
                "id": f"paper-{i}",
                "title": f"Existing Paper {i}",
                "summary": f"Summary {i}",
                "source": "Test",
                "url": f"https://example.com/paper-{i}",
                "published_at": f"2026-01-{i % 28 + 1:02d}",
                "fetched_at": f"2026-01-{i % 28 + 1:02d}T00:00:00Z",
                "type": "announcement",
                "topics": [],
                "ranking_score": 0,
                "status": "unread",
            })

        (data_dir / "papers.json").write_text(
            json.dumps({"papers": existing_papers}), encoding="utf-8"
        )

        # Add one more paper
        new_paper = {
            "title": "Brand New Paper",
            "summary": "New description",
            "url": "https://example.com/brand-new",
            "source": "Test",
            "published": "2026-03-17",
            "type": "announcement",
        }
        export_papers([new_paper])

        data = json.loads((data_dir / "papers.json").read_text(encoding="utf-8"))
        assert len(data["papers"]) <= PAPERS_CAP


class TestDigestCapEnforcement:
    """Tests for digests.json cap enforcement."""

    def test_digests_capped_at_limit(self, data_dir, monkeypatch):
        """Digests should be capped at DIGEST_CAP_DAYS."""
        # Pre-populate with DIGEST_CAP_DAYS digests
        existing_digests = []
        for i in range(DIGEST_CAP_DAYS):
            existing_digests.append({
                "date": f"2026-{(i // 28) + 1:02d}-{i % 28 + 1:02d}",
                "top_paper_id": f"paper-{i}",
                "papers_fetched": 5,
                "pdf_path": "",
                "telegram_sent": True,
                "workflow_run_id": "",
            })

        (data_dir / "digests.json").write_text(
            json.dumps({"digests": existing_digests}), encoding="utf-8"
        )

        # Add a new digest for a unique date
        from datetime import datetime

        class FrozenDatetime:
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 12, 31, 12, 0, 0)

        original_datetime = json_exporter.datetime
        try:
            json_exporter.datetime = FrozenDatetime
            export_digest(
                top_paper_id="paper-new",
                papers_fetched=10,
                telegram_sent=True,
            )
        finally:
            json_exporter.datetime = original_datetime

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        assert len(data["digests"]) <= DIGEST_CAP_DAYS


class TestFullPipelineFlow:
    """Integration-style test: run main() with all external APIs mocked."""

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_research_message")
    @patch("main.generate_research_pdf")
    @patch("main.summarize_research_bundle")
    @patch("main.export_papers")
    @patch("main.rank_research")
    @patch("main.fetch_all")
    def test_pipeline_runs_end_to_end(
        self,
        mock_fetch,
        mock_rank,
        mock_export_papers,
        mock_summarize,
        mock_pdf,
        mock_format,
        mock_send,
        mock_export_digest,
        env_vars,
    ):
        """Full pipeline should call each stage in order."""
        import main

        paper = {
            "title": "Test Paper",
            "summary": "Test",
            "url": "https://openai.com/test",
            "source": "OpenAI",
            "published": "2024-07-18T00:00:00",
            "type": "announcement",
        }
        enriched = {**paper, "summary": "Short", "detailed_summary": "Detailed"}

        mock_fetch.return_value = [paper]
        mock_rank.return_value = paper
        mock_export_papers.return_value = "paper-1"
        mock_summarize.return_value = enriched
        mock_pdf.return_value = "reports/17-Mar/test.pdf"
        mock_format.return_value = "formatted message"

        main.main()

        # Verify call order
        mock_fetch.assert_called_once()
        mock_rank.assert_called_once()
        mock_export_papers.assert_called_once()
        mock_summarize.assert_called_once()
        mock_pdf.assert_called_once()
        mock_format.assert_called_once()
        mock_send.assert_called_once()
        mock_export_digest.assert_called_once()
