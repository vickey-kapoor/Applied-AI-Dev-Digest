"""Unit tests for JSON export utilities."""

import json
import shutil
import uuid
from pathlib import Path

import pytest

from src import json_exporter


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


class TestExportPapers:
    """Tests for paper export behavior."""

    def test_export_papers_returns_existing_top_paper_id(self, data_dir, sample_paper):
        """Top-paper links should survive when the paper already exists."""
        existing = {
            "papers": [
                {
                    "id": "paper-123",
                    "title": sample_paper["title"],
                    "summary": sample_paper["summary"],
                    "source": sample_paper["source"],
                    "url": sample_paper["url"],
                    "published_at": sample_paper["published"],
                    "fetched_at": "2026-03-13T00:00:00Z",
                    "type": sample_paper["type"],
                    "topics": [],
                    "ranking_score": 0,
                    "status": "unread",
                }
            ]
        }
        (data_dir / "papers.json").write_text(json.dumps(existing), encoding="utf-8")

        top_paper_id = json_exporter.export_papers([sample_paper], ranked_paper=sample_paper)

        assert top_paper_id == "paper-123"

    def test_export_papers_uses_deterministic_ids_for_new_papers(self, data_dir, sample_paper):
        """New paper IDs should be stable for the same source record."""
        first_id = json_exporter.export_papers([sample_paper], ranked_paper=sample_paper)
        stored = json.loads((data_dir / "papers.json").read_text(encoding="utf-8"))
        stored["papers"] = []
        (data_dir / "papers.json").write_text(json.dumps(stored), encoding="utf-8")

        second_id = json_exporter.export_papers([sample_paper], ranked_paper=sample_paper)

        assert first_id == second_id

    def test_save_json_writes_atomically(self, data_dir):
        """Atomic writes should not leave temporary files behind."""
        json_exporter.save_json("papers.json", {"papers": []})

        assert (data_dir / "papers.json").exists()
        temp_files = list(data_dir.glob(".*.tmp"))
        assert temp_files == []


class TestGetSentTopPaperIds:
    """Tests for get_sent_top_paper_ids."""

    def test_returns_ids_of_sent_digests(self, data_dir):
        digests = {
            "digests": [
                {"date": "2026-03-24", "top_paper_id": "id-a", "telegram_sent": True},
                {"date": "2026-03-23", "top_paper_id": "id-b", "telegram_sent": True},
                {"date": "2026-03-22", "top_paper_id": "id-c", "telegram_sent": False},
            ]
        }
        (data_dir / "digests.json").write_text(json.dumps(digests), encoding="utf-8")

        result = json_exporter.get_sent_top_paper_ids()
        assert result == {"id-a", "id-b"}

    def test_returns_empty_set_when_no_digests(self, data_dir):
        result = json_exporter.get_sent_top_paper_ids()
        assert result == set()

    def test_skips_empty_paper_ids(self, data_dir):
        digests = {
            "digests": [
                {"date": "2026-03-24", "top_paper_id": "", "telegram_sent": True},
                {"date": "2026-03-23", "top_paper_id": "id-x", "telegram_sent": True},
            ]
        }
        (data_dir / "digests.json").write_text(json.dumps(digests), encoding="utf-8")

        result = json_exporter.get_sent_top_paper_ids()
        assert result == {"id-x"}


class TestExportDigest:
    """Tests for digest export behavior."""

    def test_export_digest_updates_existing_entry(self, data_dir):
        """Digest exports should update the current day instead of duplicating it."""
        existing = {
            "digests": [
                {
                    "date": "2026-03-13",
                    "top_paper_id": "",
                    "papers_fetched": 1,
                    "pdf_path": "",
                    "telegram_sent": False,
                    "workflow_run_id": "",
                }
            ]
        }
        (data_dir / "digests.json").write_text(json.dumps(existing), encoding="utf-8")

        class FrozenDatetime:
            @classmethod
            def now(cls, tz=None):
                from datetime import datetime

                return datetime(2026, 3, 13, 12, 0, 0)

        original_datetime = json_exporter.datetime
        try:
            json_exporter.datetime = FrozenDatetime
            json_exporter.export_digest(
                top_paper_id="paper-1",
                papers_fetched=5,
                pdf_path="reports/13-Mar/test.pdf",
                telegram_sent=True,
                workflow_run_id="run-1",
            )
        finally:
            json_exporter.datetime = original_datetime

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        assert len(data["digests"]) == 1
        assert data["digests"][0]["top_paper_id"] == "paper-1"
        assert data["digests"][0]["telegram_sent"] is True
