"""Tests for src/digest_claim.py — the one-send-per-day claim.

The duplicate these guard against: two runs that overlap, where the loser's
committed state file predates the winner's send. See the module docstring.
"""

import logging
import sys
from unittest.mock import patch

import pytest

from src import digest_claim


@pytest.fixture(autouse=True)
def restore_log_streams():
    """The CLI re-points the app logger at stderr, which is global state.

    Left in place it outlives the test: pytest closes its captured stderr at
    teardown and the next flush raises on a closed file.
    """
    app = logging.getLogger("ai_research_digest")
    original = list(app.handlers)
    yield
    for handler in list(app.handlers):
        if handler not in original:
            # Assigned rather than closed: the handler holds capsys's stderr,
            # which capsys closes, and any flush of it raises.
            handler.stream = sys.__stderr__
            app.removeHandler(handler)
    app.handlers = original


@pytest.fixture(autouse=True)
def kv_env(monkeypatch):
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
    monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")


class TestClaimToday:
    def test_winner_may_send(self):
        with patch("src.digest_claim.kv_set_if_absent", return_value=True) as nx:
            assert digest_claim.claim_today() is True
        assert nx.call_args[0][0].startswith("digest:claim:")

    def test_loser_may_not_send(self):
        with patch("src.digest_claim.kv_set_if_absent", return_value=False):
            assert digest_claim.claim_today() is False

    def test_only_one_of_two_concurrent_runs_wins(self):
        """What the real bug looked like: both runs read the day as unsent."""
        store: dict[str, object] = {}

        def fake_nx(key, value, ttl_seconds=None):
            if key in store:
                return False
            store[key] = value
            return True

        with patch("src.digest_claim.kv_set_if_absent", side_effect=fake_nx):
            first = digest_claim.claim_today()
            second = digest_claim.claim_today()

        assert [first, second] == [True, False]

    def test_the_key_is_dated_so_tomorrow_is_a_new_day(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        chicago = ZoneInfo("America/Chicago")
        with patch("src.digest_claim.kv_set_if_absent", return_value=True) as nx:
            with patch(
                "src.digest_claim.now_local",
                return_value=datetime(2026, 10, 20, 12, 1, tzinfo=chicago),
            ):
                digest_claim.claim_today()
            with patch(
                "src.digest_claim.now_local",
                return_value=datetime(2026, 10, 21, 12, 1, tzinfo=chicago),
            ):
                digest_claim.claim_today()

        assert nx.call_args_list[0][0][0] == "digest:claim:2026-10-20"
        assert nx.call_args_list[1][0][0] == "digest:claim:2026-10-21"

    def test_the_claim_carries_a_ttl(self):
        """A run killed mid-send must not claim the day forever."""
        with patch("src.digest_claim.kv_set_if_absent", return_value=True) as nx:
            digest_claim.claim_today()
        ttl = nx.call_args[0][2] if len(nx.call_args[0]) > 2 else nx.call_args[1]["ttl_seconds"]
        assert ttl == digest_claim.CLAIM_TTL_SECONDS
        assert ttl > 86400, "the TTL must outlast a day's run, not cut it short"

    def test_force_sends_even_when_the_day_is_claimed(self):
        with patch("src.digest_claim.kv_set_if_absent", return_value=False):
            with patch("src.digest_claim.kv_delete") as delete:
                assert digest_claim.claim_today(force=True) is True
        assert delete.called, "force must clear the existing claim"

    def test_an_unconfigured_kv_does_not_block_a_local_run(self, monkeypatch):
        monkeypatch.delenv("KV_REST_API_URL", raising=False)
        monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
        with patch("src.digest_claim.kv_set_if_absent") as nx:
            assert digest_claim.claim_today() is True
        assert not nx.called


class TestReleaseToday:
    def test_release_deletes_todays_key(self):
        with patch("src.digest_claim.kv_delete") as delete:
            digest_claim.release_today()
        assert delete.call_args[0][0].startswith("digest:claim:")

    def test_release_is_a_no_op_without_kv(self, monkeypatch):
        monkeypatch.delenv("KV_REST_API_URL", raising=False)
        monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
        with patch("src.digest_claim.kv_delete") as delete:
            digest_claim.release_today()
        assert not delete.called


class TestCli:
    """The workflow captures stdout into $GITHUB_OUTPUT, so stdout is a
    contract: the decision and nothing else."""

    def test_claim_prints_only_the_decision(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["digest_claim", "claim"])
        with patch("src.digest_claim.kv_set_if_absent", return_value=True):
            assert digest_claim.main() == 0
        assert capsys.readouterr().out == "true\n"

    def test_a_declined_claim_still_exits_zero(self, capsys, monkeypatch):
        """A non-zero exit would read as a broken step rather than a decision."""
        monkeypatch.setattr("sys.argv", ["digest_claim", "claim"])
        with patch("src.digest_claim.kv_set_if_absent", return_value=False):
            assert digest_claim.main() == 0
        assert capsys.readouterr().out == "false\n"

    def test_kv_logging_does_not_reach_stdout(self, capsys, monkeypatch):
        """kv_client logs to stdout by default, which would corrupt the output."""
        monkeypatch.setattr("sys.argv", ["digest_claim", "claim"])

        def log_and_win(*args, **kwargs):
            logging.getLogger("ai_research_digest.kv_client").info("KV SET x NX")
            return True

        with patch("src.digest_claim.kv_set_if_absent", side_effect=log_and_win):
            digest_claim.main()
        assert capsys.readouterr().out == "true\n"

    def test_force_flag_is_accepted(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["digest_claim", "claim", "--force"])
        with patch("src.digest_claim.kv_set_if_absent", return_value=False):
            with patch("src.digest_claim.kv_delete"):
                assert digest_claim.main() == 0
        assert capsys.readouterr().out == "true\n"

    def test_release_prints_nothing(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["digest_claim", "release"])
        with patch("src.digest_claim.kv_delete"):
            assert digest_claim.main() == 0
        assert capsys.readouterr().out == ""

    def test_an_unknown_command_is_a_usage_error(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["digest_claim", "nonsense"])
        assert digest_claim.main() == 2
