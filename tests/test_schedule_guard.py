"""Tests for the polling schedule guard."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.schedule_guard import is_due, load_state, mark_ran, save_state

CHICAGO = ZoneInfo("America/Chicago")
REPO_ROOT = Path(__file__).resolve().parent.parent


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=CHICAGO)


class TestDailyDue:
    """The daily digest is due once local noon has passed, once per day."""

    def test_not_due_before_target(self):
        assert is_due("daily", at(2026, 9, 7, 11, 59), {}) is False

    def test_due_exactly_at_target(self):
        assert is_due("daily", at(2026, 9, 7, 12, 0), {}) is True

    def test_still_due_later_in_the_day(self):
        """A tick delayed past noon must still deliver, not skip the day."""
        assert is_due("daily", at(2026, 9, 7, 17, 30), {}) is True

    def test_not_due_once_it_has_run_today(self):
        state = {"last_daily_date": "2026-09-07"}
        assert is_due("daily", at(2026, 9, 7, 12, 0), state) is False

    def test_due_again_the_next_day(self):
        state = {"last_daily_date": "2026-09-06"}
        assert is_due("daily", at(2026, 9, 7, 12, 0), state) is True

    def test_not_due_after_midnight_before_noon(self):
        """The old failure mode: a very late tick crossing into the next date."""
        state = {"last_daily_date": "2026-09-07"}
        assert is_due("daily", at(2026, 9, 8, 0, 30), state) is False


class TestDaylightSaving:
    """Noon local must stay noon local across the CDT/CST switch.

    This is the reason the target is a zone-aware local hour rather than a
    fixed UTC hour: a UTC cron would silently shift by an hour in November.
    """

    def test_noon_holds_either_side_of_the_switch(self):
        before = at(2026, 10, 31, 12, 0)  # CDT
        after = at(2026, 11, 2, 12, 0)    # CST

        assert before.utcoffset() != after.utcoffset(), "expected a DST change"
        assert is_due("daily", before, {}) is True
        assert is_due("daily", after, {}) is True

    def test_eleven_am_is_not_due_in_either_offset(self):
        assert is_due("daily", at(2026, 10, 31, 11, 0), {}) is False
        assert is_due("daily", at(2026, 11, 2, 11, 0), {}) is False


class TestState:
    def test_missing_file_reads_as_empty(self, tmp_path):
        assert load_state(str(tmp_path / "absent.json")) == {}

    def test_corrupt_file_reads_as_empty(self, tmp_path):
        """A damaged state file must not wedge the digest permanently off."""
        path = tmp_path / "state.json"
        path.write_text("{not json", encoding="utf-8")
        assert load_state(str(path)) == {}

    def test_non_object_reads_as_empty(self, tmp_path):
        path = tmp_path / "state.json"
        path.write_text('["unexpected"]', encoding="utf-8")
        assert load_state(str(path)) == {}

    def test_round_trip(self, tmp_path):
        path = str(tmp_path / "state.json")
        save_state({"last_daily_date": "2026-09-07"}, path)
        assert load_state(path) == {"last_daily_date": "2026-09-07"}

    def test_mark_ran_does_not_mutate_the_input(self):
        original = {"last_daily_date": "2026-09-06"}
        updated = mark_ran("daily", at(2026, 9, 7, 12, 5), original)

        assert original == {"last_daily_date": "2026-09-06"}
        assert updated["last_daily_date"] == "2026-09-07"

    def test_marking_makes_it_not_due(self):
        now = at(2026, 9, 7, 12, 5)
        assert is_due("daily", now, mark_ran("daily", now, {})) is False


class TestUnknownJob:
    """`daily` is the only job. A weekly roundup used to share this guard."""

    @pytest.mark.parametrize("job", ["hourly", "weekly"])
    def test_is_due_rejects_unknown_job(self, job):
        with pytest.raises(ValueError):
            is_due(job, at(2026, 9, 7, 12, 0), {})


class TestCommandLineContract:
    """The workflow captures stdout straight into $GITHUB_OUTPUT.

    Anything printed to stdout besides the decision would corrupt that value,
    so these tests pin the stream contract, not just the logic.
    """

    def _run(self, *args, cwd):
        return subprocess.run(
            [sys.executable, "-m", "src.schedule_guard", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_check_prints_only_the_decision_on_stdout(self, tmp_path):
        result = self._run("check", "daily", cwd=REPO_ROOT)

        assert result.returncode == 0
        assert result.stdout.strip() in ("true", "false")
        assert len(result.stdout.strip().splitlines()) == 1

    def test_diagnostics_go_to_stderr(self):
        result = self._run("check", "daily", cwd=REPO_ROOT)
        assert "due=" in result.stderr

    @pytest.mark.parametrize("job", ["hourly", "weekly"])
    def test_unknown_job_exits_nonzero(self, job):
        assert self._run("check", job, cwd=REPO_ROOT).returncode == 2

    def test_missing_arguments_exit_nonzero(self):
        assert self._run("check", cwd=REPO_ROOT).returncode == 2

    def test_mark_writes_state_and_prints_nothing_to_stdout(self, tmp_path, monkeypatch):
        state_file = tmp_path / "data" / "schedule_state.json"
        monkeypatch.setattr("src.schedule_guard.STATE_PATH", str(state_file))

        from src.schedule_guard import main

        monkeypatch.setattr(sys, "argv", ["schedule_guard", "mark", "daily"])
        assert main() == 0

        saved = json.loads(state_file.read_text(encoding="utf-8"))
        assert "last_daily_date" in saved
