"""Tests for src/kv_client.py."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.kv_client import kv_append, kv_get, kv_get_list, kv_delete, kv_trim_to_last


@pytest.fixture(autouse=True)
def kv_env(monkeypatch):
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
    monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")


def _mock_urlopen(result_value):
    """Create a mock urlopen context manager returning a KV result."""
    body = json.dumps({"result": result_value}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestKvAppend:
    @patch("src.kv_client.urlopen")
    def test_appends_value(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(3)
        result = kv_append("digest:weekly", {"title": "Test Paper"})
        assert result == 3

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode())
        assert body[0] == "RPUSH"
        assert body[1] == "digest:weekly"
        assert json.loads(body[2])["title"] == "Test Paper"

    @patch("src.kv_client.urlopen")
    def test_sends_auth_header(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(1)
        kv_append("key", "val")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer test-token"


class TestKvGetList:
    @patch("src.kv_client.urlopen")
    def test_returns_parsed_items(self, mock_urlopen):
        items = [json.dumps({"title": "Paper A"}), json.dumps({"title": "Paper B"})]
        mock_urlopen.return_value = _mock_urlopen(items)

        result = kv_get_list("digest:weekly")
        assert len(result) == 2
        assert result[0]["title"] == "Paper A"
        assert result[1]["title"] == "Paper B"

    @patch("src.kv_client.urlopen")
    def test_returns_empty_for_missing_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen([])
        result = kv_get_list("nonexistent")
        assert result == []

    @patch("src.kv_client.urlopen")
    def test_skips_unparseable_items(self, mock_urlopen):
        items = [json.dumps({"title": "Good"}), "not-valid-json"]
        mock_urlopen.return_value = _mock_urlopen(items)

        result = kv_get_list("key")
        assert len(result) == 1
        assert result[0]["title"] == "Good"


class TestKvGet:
    """kv_get is the primitive topic_config used to hand-roll for itself."""

    @patch("src.kv_client.urlopen")
    def test_parses_json_value(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(json.dumps({"model_releases": True}))
        assert kv_get("topics:config") == {"model_releases": True}

    @patch("src.kv_client.urlopen")
    def test_returns_none_for_missing_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(None)
        assert kv_get("absent") is None

    @patch("src.kv_client.urlopen")
    def test_returns_raw_string_when_not_json(self, mock_urlopen):
        """A plain string written outside this client must survive, not vanish."""
        mock_urlopen.return_value = _mock_urlopen("not json at all")
        assert kv_get("key") == "not json at all"

    @patch("src.kv_client.urlopen")
    def test_passes_through_non_string_values(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(True)
        assert kv_get("digest:paused") is True

    @patch("src.kv_client.urlopen")
    def test_issues_a_redis_get(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(None)
        kv_get("stats:topics")

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body == ["GET", "stats:topics"]


class TestKvDelete:
    @patch("src.kv_client.urlopen")
    def test_deletes_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(1)
        result = kv_delete("digest:weekly")
        assert result == 1

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body == ["DEL", "digest:weekly"]


class TestKvTrimToLast:
    """Nothing else bounds the history list now that the Sunday roundup,
    which cleared it, is gone."""

    @patch("src.kv_client.urlopen")
    def test_trims_to_the_last_n_items(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("OK")
        assert kv_trim_to_last("digest:weekly", 90) == "OK"

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body == ["LTRIM", "digest:weekly", "-90", "-1"]

    def test_rejects_a_count_that_would_empty_the_list(self):
        """LTRIM 0 -1 keeps everything and LTRIM with a positive start would
        drop the newest entries, so neither is a safe reading of count=0."""
        with pytest.raises(ValueError):
            kv_trim_to_last("digest:weekly", 0)
