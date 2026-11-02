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


class TestPaperIds:
    """The id that links a digest entry to the story it sent.

    A papers.json archive used to mint these and hand main.py whichever id it
    already held. With that gone the id is computed from the item every
    time, so it has to be stable for the same story — that is what stops the
    same pick going out twice.
    """

    def test_ids_are_deterministic_for_the_same_item(self, sample_paper):
        assert json_exporter._paper_id_for_item(sample_paper) == (
            json_exporter._paper_id_for_item(dict(sample_paper))
        )

    def test_a_different_url_is_a_different_item(self, sample_paper):
        other = {**sample_paper, "url": sample_paper["url"] + "-2"}
        assert json_exporter._paper_id_for_item(other) != (
            json_exporter._paper_id_for_item(sample_paper)
        )

    def test_save_json_writes_atomically(self, data_dir):
        """Atomic writes should not leave temporary files behind."""
        json_exporter.save_json("digests.json", {"digests": []})

        assert (data_dir / "digests.json").exists()
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
                telegram_sent=True,
                workflow_run_id="run-1",
            )
        finally:
            json_exporter.datetime = original_datetime

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        assert len(data["digests"]) == 1
        assert data["digests"][0]["top_paper_id"] == "paper-1"
        assert data["digests"][0]["telegram_sent"] is True


class TestDigestRunTimestamp:
    """The digest record must show when a run actually happened.

    GitHub's scheduler has delivered this workflow up to 9 hours late, which
    pushes a run past midnight onto the next date. Without a timestamp that
    looks like a missing day plus a duplicate one.
    """

    def test_new_entry_records_run_at(self, data_dir):
        json_exporter.export_digest(top_paper_id="p1", papers_fetched=5)

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        entry = data["digests"][0]

        assert entry["run_at"].endswith("Z")
        assert entry["run_at"].startswith(entry["date"])

    def test_second_run_same_date_preserves_the_first_timestamp(self, data_dir):
        """Two runs on one UTC date must not silently overwrite each other."""
        json_exporter.export_digest(top_paper_id="first", papers_fetched=3)
        first = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        first_run_at = first["digests"][0]["run_at"]

        json_exporter.export_digest(top_paper_id="second", papers_fetched=7)
        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))

        assert len(data["digests"]) == 1
        entry = data["digests"][0]
        assert entry["top_paper_id"] == "second"
        assert entry["papers_fetched"] == 7
        assert entry["previous_run_at"] == first_run_at

    def test_single_run_has_no_previous_marker(self, data_dir):
        json_exporter.export_digest(top_paper_id="p1", papers_fetched=5)

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        assert "previous_run_at" not in data["digests"][0]
