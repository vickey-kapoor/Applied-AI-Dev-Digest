"""Unit tests for topic configuration module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

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

    def test_eleven_topics_defined(self):
        """All AI lab development topics are present."""
        assert len(DEFAULT_TOPICS) == 11

    def test_default_enabled_count(self):
        """The six core topics plus the two applied ones — mirrors topics.ts.

        open_weights and infrastructure are category "applied" and were off by
        default, which left the digest blind to what the reader can actually
        run and to the serving and inference economics they build against.
        """
        enabled = {t["id"] for t in DEFAULT_TOPICS if t["default_enabled"]}
        expected = {
            "model_releases",
            "product_api",
            "lab_research",
            "agents_tooling",
            "benchmarks",
            "safety_system_cards",
            "open_weights",
            "infrastructure",
        }
        assert enabled == expected


class TestGetEnabledTopics:
    """Tests for _get_enabled_topics logic."""

    def test_returns_defaults_when_kv_is_none(self):
        topics = _get_enabled_topics(None)
        ids = {t["id"] for t in topics}
        assert "model_releases" in ids
        assert "product_api" in ids
        # Applied topics are on: what the reader can run, and the serving and
        # inference economics they build against.
        assert "infrastructure" in ids
        assert "open_weights" in ids
        # Emerging topics stay off.
        assert "policy_regulation" not in ids
        assert "multimodal" not in ids

    def test_respects_kv_overrides(self):
        kv_config = {
            "model_releases": False,
            "policy_regulation": True,
        }
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "model_releases" not in ids
        assert "policy_regulation" in ids

    def test_unknown_keys_in_kv_ignored(self):
        kv_config = {"unknown_topic": True, "model_releases": True}
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "model_releases" in ids
        assert "unknown_topic" not in ids


class TestGetActiveKeywords:
    """Tests for get_active_keywords."""

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_include_expected_keywords(self, mock_kv):
        keywords = get_active_keywords()
        assert "RLHF" in keywords
        assert "jailbreak" in keywords
        assert "frontier model" in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_exclude_disabled_topic_keywords(self, mock_kv):
        keywords = get_active_keywords()
        # policy_regulation and the other emerging topics stay off by default.
        # infrastructure is now on — it is core to an applied engineer — so its
        # keywords are expected here rather than absent.
        assert "EU AI Act" not in keywords
        assert "Blackwell" in keywords

    @patch("src.topic_config._fetch_kv_config")
    def test_kv_config_changes_keywords(self, mock_kv):
        """KV can enable the policy topic, adding its keywords."""
        mock_kv.return_value = {
            "policy_regulation": True,
        }
        keywords = get_active_keywords()
        assert "EU AI Act" in keywords
        assert "AI policy" in keywords

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
        assert len(topics) == 8  # six core topics plus open_weights and infrastructure
        ids = {t["id"] for t in topics}
        assert "model_releases" in ids
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
                return {"model_releases": ["my-custom-kw", "another-one"]}
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


@pytest.fixture
def kv_env(monkeypatch):
    """Credentials present, so get_feedback_weights reaches the KV call."""
    monkeypatch.setenv("KV_REST_API_URL", "https://kv.example.com")
    monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class TestGetFeedbackWeights:
    """Tests for get_feedback_weights clamping and filtering."""

    @patch("src.topic_config.kv_client.kv_get_list")
    def test_positive_feedback_boosts(self, mock_get_list, kv_env):
        today = _today()
        mock_get_list.return_value = [
            {"url": "a", "rating": 1, "topic_id": "model_releases", "date": today},
            {"url": "b", "rating": 1, "topic_id": "model_releases", "date": today},
        ]

        weights = get_feedback_weights()
        assert weights["model_releases"] == 1.1

    @patch("src.topic_config.kv_client.kv_get_list")
    def test_clamped_at_lower_bound(self, mock_get_list, kv_env):
        today = _today()
        mock_get_list.return_value = [
            {"url": f"u{i}", "rating": -1, "topic_id": "lab_research", "date": today}
            for i in range(20)
        ]

        weights = get_feedback_weights()
        assert weights["lab_research"] == 0.75

    @patch("src.topic_config.kv_client.kv_get_list")
    def test_clamped_at_upper_bound(self, mock_get_list, kv_env):
        today = _today()
        mock_get_list.return_value = [
            {"url": f"u{i}", "rating": 1, "topic_id": "model_releases", "date": today}
            for i in range(20)
        ]

        weights = get_feedback_weights()
        assert weights["model_releases"] == 1.25

    def test_returns_empty_when_no_kv(self):
        """kv_client raises without credentials; the weights must degrade to {}."""
        weights = get_feedback_weights()
        assert weights == {}

    @patch("src.topic_config.kv_client.kv_get_list", side_effect=OSError("KV down"))
    def test_returns_empty_when_kv_errors(self, mock_get_list, kv_env):
        """A KV outage must not stop ranking — weights fall back to neutral."""
        assert get_feedback_weights() == {}
