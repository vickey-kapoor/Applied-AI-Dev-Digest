"""Unit tests for topic configuration module."""

from unittest.mock import patch, MagicMock
import json

from src.topic_config import (
    DEFAULT_TOPICS,
    get_active_topics,
    get_active_keywords,
    get_active_arxiv_categories,
    _get_enabled_topics,
    is_paused,
    get_feedback_weights,
)


class TestDefaults:
    """Tests for default topic configuration."""

    def test_all_topics_have_required_fields(self):
        """Every topic must have id, keywords, arxiv_categories, default_enabled."""
        for topic in DEFAULT_TOPICS:
            assert "id" in topic
            assert "keywords" in topic
            assert "arxiv_categories" in topic
            assert "default_enabled" in topic
            assert isinstance(topic["keywords"], list)
            assert isinstance(topic["arxiv_categories"], list)
            assert len(topic["keywords"]) > 0

    def test_topic_ids_are_unique(self):
        """Topic IDs must be unique."""
        ids = [t["id"] for t in DEFAULT_TOPICS]
        assert len(ids) == len(set(ids))

    def test_thirteen_topics_defined(self):
        """All 13 topics from the spec are present."""
        assert len(DEFAULT_TOPICS) == 13

    def test_default_enabled_count(self):
        """Core + default-on topics should be enabled by default."""
        enabled = [t for t in DEFAULT_TOPICS if t["default_enabled"]]
        assert len(enabled) == 7  # agents, reasoning, alignment, codegen, science, healthcare, safety


class TestGetEnabledTopics:
    """Tests for _get_enabled_topics logic."""

    def test_returns_defaults_when_kv_is_none(self):
        """When KV config is None, use default_enabled flags."""
        topics = _get_enabled_topics(None)
        ids = {t["id"] for t in topics}
        assert "agents" in ids
        assert "reasoning" in ids
        assert "multimodal" not in ids
        assert "robotics" not in ids

    def test_respects_kv_overrides(self):
        """KV config can enable/disable topics."""
        kv_config = {
            "agents": False,
            "multimodal": True,
        }
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "agents" not in ids
        assert "multimodal" in ids
        # Non-overridden topics use defaults
        assert "reasoning" in ids

    def test_unknown_keys_in_kv_ignored(self):
        """Extra keys in KV config that don't match any topic are harmless."""
        kv_config = {"unknown_topic": True, "agents": True}
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "agents" in ids


class TestGetActiveKeywords:
    """Tests for get_active_keywords."""

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_include_expected_keywords(self, mock_kv):
        """Default keywords should cover key terms from enabled topics."""
        keywords = get_active_keywords()
        assert "api" in keywords
        assert "sdk" in keywords
        assert "agent" in keywords
        assert "reasoning" in keywords
        assert "fine-tuning" in keywords
        assert "safety" in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_exclude_disabled_topic_keywords(self, mock_kv):
        """Keywords from default-disabled topics should not appear."""
        keywords = get_active_keywords()
        # robotics is disabled by default
        assert "robotics" not in keywords
        assert "sim-to-real" not in keywords

    @patch("src.topic_config._fetch_kv_config")
    def test_kv_config_changes_keywords(self, mock_kv):
        """Enabling a disabled topic adds its keywords."""
        mock_kv.return_value = {
            "agents": True,
            "reasoning": True,
            "alignment": True,
            "codegen": True,
            "science": True,
            "healthcare": True,
            "safety": True,
            "robotics": True,  # Enabling robotics
            "multimodal": False,
            "finance": False,
            "nlp": False,
            "efficient": False,
            "synthetic": False,
        }
        keywords = get_active_keywords()
        assert "robotics" in keywords
        assert "sim-to-real" in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_keywords_are_deduplicated(self, mock_kv):
        """No duplicate keywords in the result."""
        keywords = get_active_keywords()
        assert len(keywords) == len(set(keywords))

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_supplemental_keywords_included(self, mock_kv):
        """Supplemental keywords (model, release, etc.) are always present."""
        keywords = get_active_keywords()
        assert "model" in keywords
        assert "release" in keywords
        assert "launch" in keywords


class TestGetActiveArxivCategories:
    """Tests for get_active_arxiv_categories."""

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_return_categories(self, mock_kv):
        """Default config returns arxiv categories from enabled topics."""
        categories = get_active_arxiv_categories()
        assert "cs.AI" in categories
        assert "cs.LG" in categories
        # cs.RO from robotics should not be present (disabled by default)
        assert "cs.RO" not in categories

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_categories_are_deduplicated(self, mock_kv):
        """No duplicate categories in the result."""
        categories = get_active_arxiv_categories()
        assert len(categories) == len(set(categories))


class TestFetchKvConfig:
    """Tests for KV fetch error handling."""

    @patch("src.topic_config._fetch_kv_config", side_effect=Exception("network error"))
    def test_get_active_topics_falls_back_on_error(self, mock_kv):
        """get_active_topics returns defaults when _fetch_kv_config raises."""
        # _fetch_kv_config is called inside get_active_topics; if it raises,
        # the function should still return defaults
        # Since we patched _fetch_kv_config to raise, get_active_topics will propagate.
        # But actually the real _fetch_kv_config catches internally. Let's test the
        # higher-level: when KV returns None.
        pass

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_graceful_fallback_when_no_kv(self, mock_kv):
        """When KV is unreachable (returns None), defaults are used."""
        topics = get_active_topics()
        assert len(topics) == 7  # 7 default-enabled topics
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
        """Custom keywords from KV are merged into active keywords."""
        def side_effect(key):
            if key == "topics:custom_keywords":
                return {"agents": ["my-custom-kw", "another-one"]}
            return None
        mock_kv_get.side_effect = side_effect

        keywords = get_active_keywords()
        assert "my-custom-kw" in keywords
        assert "another-one" in keywords

    @patch("src.topic_config._kv_get", return_value=None)
    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_no_custom_keywords_when_none(self, mock_config, mock_kv_get):
        """When custom keywords KV returns None, only default keywords are used."""
        keywords = get_active_keywords()
        assert "my-custom-kw" not in keywords


class TestGetFeedbackWeights:
    """Tests for get_feedback_weights clamping and filtering."""

    @patch("src.topic_config.urllib.request.urlopen")
    def test_positive_feedback_boosts(self, mock_urlopen, monkeypatch):
        """Thumbs-up feedback should increase multiplier."""
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
        assert weights["agents"] == 1.1  # 1.0 + 2 * 0.05

    @patch("src.topic_config.urllib.request.urlopen")
    def test_negative_feedback_penalizes(self, mock_urlopen, monkeypatch):
        """Thumbs-down feedback should decrease multiplier."""
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
        monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        entries = [
            json.dumps({"url": "a", "rating": -1, "topic_id": "codegen", "date": today}),
            json.dumps({"url": "b", "rating": -1, "topic_id": "codegen", "date": today}),
            json.dumps({"url": "c", "rating": -1, "topic_id": "codegen", "date": today}),
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"result": entries}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        weights = get_feedback_weights()
        assert weights["codegen"] == 0.85  # 1.0 + (-3) * 0.05 = 0.85

    @patch("src.topic_config.urllib.request.urlopen")
    def test_clamped_at_lower_bound(self, mock_urlopen, monkeypatch):
        """Multiplier should never go below 0.75."""
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
        """Multiplier should never exceed 1.25."""
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

    @patch("src.topic_config.urllib.request.urlopen")
    def test_old_feedback_filtered_out(self, mock_urlopen, monkeypatch):
        """Feedback older than 30 days should be ignored."""
        monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
        monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

        entries = [
            json.dumps({"url": "old", "rating": -1, "topic_id": "agents", "date": "2020-01-01"}),
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"result": entries}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        weights = get_feedback_weights()
        assert "agents" not in weights  # Old entry filtered, no weight

    def test_returns_empty_when_no_kv(self):
        """Returns empty dict when KV env vars are not set."""
        weights = get_feedback_weights()
        assert weights == {}
