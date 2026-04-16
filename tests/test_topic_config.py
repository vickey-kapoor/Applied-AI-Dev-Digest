"""Unit tests for topic configuration module."""

from unittest.mock import patch, MagicMock
import json

from src.topic_config import (
    DEFAULT_TOPICS,
    get_active_topics,
    get_active_keywords,
    _get_enabled_topics,
    is_paused,
    get_feedback_weights,
)


class TestDefaults:
    """Tests for default topic configuration."""

    def test_all_topics_have_required_fields(self):
        """Every topic must have id, keywords, default_enabled."""
        for topic in DEFAULT_TOPICS:
            assert "id" in topic
            assert "keywords" in topic
            assert "default_enabled" in topic
            assert isinstance(topic["keywords"], list)
            assert len(topic["keywords"]) > 0

    def test_topic_ids_are_unique(self):
        ids = [t["id"] for t in DEFAULT_TOPICS]
        assert len(ids) == len(set(ids))

    def test_ten_topics_defined(self):
        """All dev-focused topics are present (including computer_use)."""
        assert len(DEFAULT_TOPICS) == 11

    def test_default_enabled_count(self):
        """Only computer_use should be enabled by default."""
        enabled = [t for t in DEFAULT_TOPICS if t["default_enabled"]]
        assert len(enabled) == 1


class TestGetEnabledTopics:
    """Tests for _get_enabled_topics logic."""

    def test_returns_defaults_when_kv_is_none(self):
        topics = _get_enabled_topics(None)
        ids = {t["id"] for t in topics}
        assert "computer_use" in ids
        assert "hardware" not in ids

    def test_respects_kv_overrides(self):
        kv_config = {
            "agents": False,
            "hardware": True,
        }
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "agents" not in ids
        assert "computer_use" in ids
        assert "hardware" in ids

    def test_unknown_keys_in_kv_ignored(self):
        kv_config = {"unknown_topic": True, "agents": True}
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "computer_use" in ids
        assert "agents" in ids


class TestGetActiveKeywords:
    """Tests for get_active_keywords."""

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_include_expected_keywords(self, mock_kv):
        keywords = get_active_keywords()
        assert "computer use" in keywords
        assert "browser-use" in keywords or "browser use" in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_exclude_disabled_topic_keywords(self, mock_kv):
        keywords = get_active_keywords()
        assert "CUDA" not in keywords
        assert "fine-tuning" not in keywords

    @patch("src.topic_config._fetch_kv_config")
    def test_kv_config_changes_keywords(self, mock_kv):
        """Even if KV enables other topics, active keywords stay computer_use only."""
        mock_kv.return_value = {
            "models": True,
            "apis": True,
            "frameworks": True,
            "inference": True,
            "finetuning": True,
            "rag": True,
            "agents": True,
            "opensource": True,
            "safety": True,
            "hardware": True,
        }
        keywords = get_active_keywords()
        assert "GPU" not in keywords
        assert "CUDA" not in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_keywords_are_deduplicated(self, mock_kv):
        keywords = get_active_keywords()
        assert len(keywords) == len(set(keywords))

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_no_generic_supplemental_keywords(self, mock_kv):
        keywords = get_active_keywords()
        assert "model" not in keywords
        assert "release" not in keywords
        assert "launch" not in keywords


class TestFetchKvConfig:
    """Tests for KV fetch error handling."""

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_graceful_fallback_when_no_kv(self, mock_kv):
        topics = get_active_topics()
        assert len(topics) == 1  # computer_use only
        keywords = get_active_keywords()
        assert len(keywords) > 0


class TestIsPaused:
    """Tests for is_paused."""

    @patch("src.topic_config._kv_get", return_value=True)
    def test_paused_when_true(self, mock_kv):
        assert is_paused() is True

    @patch("src.topic_config._kv_get", return_value=False)
    def test_not_paused_when_false(self, mock_kv):
        assert is_paused() is False

    @patch("src.topic_config._kv_get", return_value=None)
    def test_not_paused_when_none(self, mock_kv):
        assert is_paused() is False

    @patch("src.topic_config._kv_get", return_value="true")
    def test_paused_when_string_true(self, mock_kv):
        assert is_paused() is True


class TestCustomKeywords:
    """Tests for custom keyword merging."""

    @patch("src.topic_config._kv_get")
    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_custom_keywords_merged(self, mock_config, mock_kv_get):
        def side_effect(key):
            if key == "topics:custom_keywords":
                return {"computer_use": ["my-custom-kw", "another-one"]}
            return None
        mock_kv_get.side_effect = side_effect

        keywords = get_active_keywords()
        assert "my-custom-kw" in keywords
        assert "another-one" in keywords

    @patch("src.topic_config._kv_get", return_value=None)
    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_no_custom_keywords_when_none(self, mock_config, mock_kv_get):
        keywords = get_active_keywords()
        assert "my-custom-kw" not in keywords


class TestGetFeedbackWeights:
    """Tests for get_feedback_weights clamping and filtering."""

    @patch("src.topic_config.urllib.request.urlopen")
    def test_positive_feedback_boosts(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
        monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = [
            json.dumps({"url": "a", "rating": 1, "topic_id": "agents", "date": today}),
            json.dumps({"url": "b", "rating": 1, "topic_id": "agents", "date": today}),
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"result": entries}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        weights = get_feedback_weights()
        assert weights["agents"] == 1.1

    @patch("src.topic_config.urllib.request.urlopen")
    def test_clamped_at_lower_bound(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
        monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = [
            json.dumps({"url": f"u{i}", "rating": -1, "topic_id": "safety", "date": today})
            for i in range(20)
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"result": entries}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        weights = get_feedback_weights()
        assert weights["safety"] == 0.75

    @patch("src.topic_config.urllib.request.urlopen")
    def test_clamped_at_upper_bound(self, mock_urlopen, monkeypatch):
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
        monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = [
            json.dumps({"url": f"u{i}", "rating": 1, "topic_id": "agents", "date": today})
            for i in range(20)
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"result": entries}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        weights = get_feedback_weights()
        assert weights["agents"] == 1.25

    def test_returns_empty_when_no_kv(self):
        weights = get_feedback_weights()
        assert weights == {}
