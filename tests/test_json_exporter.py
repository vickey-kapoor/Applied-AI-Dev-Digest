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
                pdf_path="reports/2026/2026-03-13/test.pdf",
                telegram_sent=True,
                workflow_run_id="run-1",
            )
        finally:
            json_exporter.datetime = original_datetime

        data = json.loads((data_dir / "digests.json").read_text(encoding="utf-8"))
        assert len(data["digests"]) == 1
        assert data["digests"][0]["top_paper_id"] == "paper-1"
        assert data["digests"][0]["telegram_sent"] is True


class TestExtractTopics:
    """Tests for topic tagging, which reads the configured taxonomy."""

    def test_uses_configured_topic_names(self):
        """Tags come from DEFAULT_TOPICS, not a private copy that can drift."""
        from src.topic_config import DEFAULT_TOPICS

        valid_names = {t["name"] for t in DEFAULT_TOPICS}
        topics = json_exporter.extract_topics({
            "title": "Introducing our new frontier model",
            "summary": "Tops SWE-bench and ships in the developer api today",
        })

        assert topics
        assert set(topics).issubset(valid_names)

    def test_assigned_topic_id_is_listed_first(self):
        """An item already tagged by the fetcher leads with that topic."""
        topics = json_exporter.extract_topics({
            "title": "Tops SWE-bench",
            "summary": "benchmark results",
            "topic_id": "model_releases",
        })

        assert topics[0] == "Model Releases"

    def test_no_match_returns_empty(self):
        topics = json_exporter.extract_topics({
            "title": "Nothing relevant here",
            "summary": "just words",
        })

        assert topics == []

    def test_caps_at_five(self):
        """Tag list stays bounded even when an item matches many topics."""
        topics = json_exporter.extract_topics({
            "title": "New frontier model with open weights and a system card",
            "summary": (
                "agentic tool use, multimodal vision-language, benchmark results, "
                "developer api pricing, inference on gpu cluster, EU AI Act compliance, "
                "enterprise deployment, technical report on post-training"
            ),
        })

        assert len(topics) <= 5


class TestStructuredBriefPersistence:
    """The structured brief must survive into papers.json."""

    def test_summary_fields_are_persisted(self, data_dir, sample_paper_with_summary):
        json_exporter.export_papers(
            [sample_paper_with_summary], ranked_paper=sample_paper_with_summary
        )

        data = json.loads((data_dir / "papers.json").read_text(encoding="utf-8"))
        paper = data["papers"][0]

        assert paper["what_shipped"] == sample_paper_with_summary["what_shipped"]
        assert paper["capabilities"] == sample_paper_with_summary["capabilities"]
        assert paper["availability"] == sample_paper_with_summary["availability"]
        assert paper["why_it_matters"] == sample_paper_with_summary["why_it_matters"]
        assert paper["caveats"] == sample_paper_with_summary["caveats"]
        assert paper["release_type"] == sample_paper_with_summary["release_type"]

    def test_unsummarized_items_omit_brief_fields(self, data_dir, sample_paper):
        """Items the summarizer never touched carry no empty brief keys."""
        json_exporter.export_papers([sample_paper])

        data = json.loads((data_dir / "papers.json").read_text(encoding="utf-8"))
        paper = data["papers"][0]

        assert "what_shipped" not in paper
        assert "release_type" not in paper


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
