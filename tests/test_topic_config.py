"""Unit tests for topic configuration module."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.topic_config import (
    DEFAULT_TOPICS,
    RETIRED_TOPIC_IDS,
    best_topic_id,
    score_topics,
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

    def test_nine_topics_defined(self):
        """All AI lab development topics are present.

        Eleven until the 28-Oct-2026 audit retired enterprise_deployment and
        policy_regulation, neither of which had ever produced a digest.
        """
        assert len(DEFAULT_TOPICS) == 9

    def test_retired_topics_are_not_defined(self):
        ids = {t["id"] for t in DEFAULT_TOPICS}
        assert ids.isdisjoint(RETIRED_TOPIC_IDS)

    def test_no_keyword_belongs_to_two_topics(self):
        """"Gemma" was in model_releases and open_weights, and first-match
        tagging meant open_weights never once received it."""
        owner: dict[str, str] = {}
        for topic in DEFAULT_TOPICS:
            for kw in list(topic["keywords"]) + list(topic.get("weak_keywords", ())):
                key = kw.lower()
                assert key not in owner, f"{kw} is also under {owner.get(key)}"
                owner[key] = topic["id"]

    def test_every_topic_is_enabled_by_default(self):
        """Mirrors topics.ts.

        A disabled topic is inert rather than merely untagged: it contributes
        no keywords to the gate, so while multimodal was off a video or speech
        model launch was dropped outright from the open sources. The audit
        turned it on and retired the two topics that earned nothing, which
        leaves nothing off.
        """
        enabled = {t["id"] for t in DEFAULT_TOPICS if t["default_enabled"]}
        assert enabled == {t["id"] for t in DEFAULT_TOPICS}


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
        # Multimodal is on as of the 28-Oct-2026 audit; the retired topics
        # are not definable at all.
        assert "multimodal" in ids
        assert ids.isdisjoint(RETIRED_TOPIC_IDS)

    def test_respects_kv_overrides(self):
        kv_config = {
            "model_releases": False,
            "multimodal": True,
        }
        topics = _get_enabled_topics(kv_config)
        ids = {t["id"] for t in topics}
        assert "model_releases" not in ids
        assert "multimodal" in ids

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
        assert "system card" in keywords
        assert "frontier model" in keywords
        # A weak keyword gates even though it barely tags.
        assert "Claude" in keywords

    @patch("src.topic_config._fetch_kv_config", return_value=None)
    def test_defaults_exclude_removed_keywords(self, mock_kv):
        keywords = get_active_keywords()
        # Measured casualties of substring matching: 3 of 4 "serving" matches
        # were the word *preserving*, and "jailbreak" admitted a Nintendo
        # Switch jailbreak from Hacker News.
        assert "serving" not in keywords
        assert "jailbreak" not in keywords
        # A keyword that never matched anything in 15 months.
        assert "model card" not in keywords
        assert "Blackwell" in keywords

    @patch("src.topic_config._fetch_kv_config")
    def test_kv_config_can_switch_a_topic_off(self, mock_kv):
        """KV can disable a topic, removing its keywords from the gate."""
        mock_kv.return_value = {
            "multimodal": False,
        }
        keywords = get_active_keywords()
        assert "world simulation" not in keywords
        assert "Sora" not in keywords
        assert "benchmark" in keywords

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
        assert len(topics) == 9  # every topic is on by default
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


class TestTopicScoring:
    """Tests for score_topics and best_topic_id.

    Tagging used to take the first topic in list order whose keywords matched,
    and model_releases is first and carries the brand names. Over the 60 days
    to 27-Oct-2026 that gave it 116 of 213 tagged items, 98 of them on a brand
    name alone: "How the Claude Code team does code review" was a model
    release, and so was an SDK version bump.
    """

    def test_substance_outranks_a_brand_name(self):
        text = "Gemma 4 is an open-weight model you can run locally"
        assert best_topic_id(text) == "open_weights"

    def test_a_brand_name_still_tags_when_nothing_else_matches(self):
        assert best_topic_id("Claude Duet") == "model_releases"

    def test_more_matches_win_over_fewer(self):
        text = "Our coding agent now supports tool use and agent skills on GPT-6"
        assert best_topic_id(text) == "agents_tooling"

    def test_longer_keyword_breaks_a_tie(self):
        # One strong keyword each: "benchmark" (9) against "AI agent" (8).
        text = "Benchmarking AI agent harnesses"
        assert best_topic_id(text) == "benchmarks"

    def test_list_order_breaks_a_remaining_tie(self):
        """Equal score and equal specificity keeps the dashboard's order."""
        ids = [t["id"] for t in DEFAULT_TOPICS]
        text = "technical report on inference"  # lab_research vs infrastructure
        ranked = [t["id"] for t in score_topics(text)]
        assert ranked[:2] == sorted(ranked[:2], key=ids.index)

    def test_no_match_returns_nothing(self):
        assert best_topic_id("A quiet day in the garden") == ""
        assert score_topics("A quiet day in the garden") == []

    def test_only_the_given_topics_are_considered(self):
        only_benchmarks = [t for t in DEFAULT_TOPICS if t["id"] == "benchmarks"]
        assert best_topic_id("Claude Duet", only_benchmarks) == ""
