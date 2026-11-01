"""Tests for src/kv_client.py."""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.kv_client import (
    kv_delete,
    kv_set_if_absent,
)


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


class TestKvDelete:
    @patch("src.kv_client.urlopen")
    def test_deletes_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(1)
        result = kv_delete("digest:claim:2026-11-01")
        assert result == 1

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body == ["DEL", "digest:claim:2026-11-01"]


class TestKvSetIfAbsent:
    """Redis replies "OK" to the one caller that set the key and null to the
    rest, which is what makes this usable as a claim between two runners."""

    @patch("src.kv_client.urlopen")
    def test_true_when_this_caller_set_the_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("OK")
        assert kv_set_if_absent("digest:claim:2026-10-20", {"at": "noon"}) is True

    @patch("src.kv_client.urlopen")
    def test_false_when_the_key_already_exists(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(None)
        assert kv_set_if_absent("digest:claim:2026-10-20", {"at": "noon"}) is False

    @patch("src.kv_client.urlopen")
    def test_sends_set_nx(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("OK")
        kv_set_if_absent("key", {"a": 1})

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body[0] == "SET"
        assert body[1] == "key"
        assert json.loads(body[2]) == {"a": 1}
        assert "NX" in body

    @patch("src.kv_client.urlopen")
    def test_ttl_is_passed_as_ex_seconds(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("OK")
        kv_set_if_absent("key", "v", ttl_seconds=120)

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert body[-2:] == ["EX", "120"]

    @patch("src.kv_client.urlopen")
    def test_no_ttl_sends_no_expiry(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen("OK")
        kv_set_if_absent("key", "v")

        body = json.loads(mock_urlopen.call_args[0][0].data.decode())
        assert "EX" not in body

    def test_a_nonsense_ttl_is_rejected(self):
        with pytest.raises(ValueError):
            kv_set_if_absent("key", "v", ttl_seconds=0)
