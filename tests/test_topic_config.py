"""Unit tests for topic configuration module."""

from src.topic_config import (
    DEFAULT_TOPICS,
    RETIRED_TOPIC_IDS,
    best_topic_id,
    names_a_model_version,
    score_topics,
    get_active_topics,
    get_active_keywords,
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


class TestGetActiveTopics:
    """Tests for which topics the digest runs against."""

    def test_every_default_topic_is_active(self):
        topics = get_active_topics()
        ids = {t["id"] for t in topics}
        assert len(topics) == 9
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

    def test_a_topic_disabled_in_the_table_drops_out(self):
        """default_enabled is the only switch now that KV config is gone."""
        topic = next(t for t in DEFAULT_TOPICS if t["id"] == "multimodal")
        topic["default_enabled"] = False
        try:
            assert "multimodal" not in {t["id"] for t in get_active_topics()}
        finally:
            topic["default_enabled"] = True


class TestGetActiveKeywords:
    """Tests for get_active_keywords."""

    def test_defaults_include_expected_keywords(self):
        keywords = get_active_keywords()
        assert "RLHF" in keywords
        assert "system card" in keywords
        assert "frontier model" in keywords
        # A weak keyword gates even though it barely tags.
        assert "Claude" in keywords

    def test_defaults_exclude_removed_keywords(self):
        keywords = get_active_keywords()
        # Measured casualties of substring matching: 3 of 4 "serving" matches
        # were the word *preserving*, and "jailbreak" admitted a Nintendo
        # Switch jailbreak from Hacker News.
        assert "serving" not in keywords
        assert "jailbreak" not in keywords
        # A keyword that never matched anything in 15 months.
        assert "model card" not in keywords
        assert "Blackwell" in keywords

    def test_keywords_are_deduplicated(self):
        keywords = get_active_keywords()
        assert len(keywords) == len(set(keywords))

    def test_no_generic_supplemental_keywords(self):
        keywords = get_active_keywords()
        assert "model" not in keywords
        assert "release" not in keywords
        assert "launch" not in keywords


class TestTopicScoring:
    """Tests for score_topics and best_topic_id.

    Tagging used to take the first topic in list order whose keywords matched,
    and model_releases is first and carries the brand names. Over the 60 days
    to 27-Oct-2026 that gave it 116 of 213 tagged items, 98 of them on a brand
    name alone: "How the Claude Code team does code review" was a model
    release, and so was an SDK version bump.
    """

    def test_substance_outranks_a_brand_name(self):
        text = "Gemma is an open-weight model you can run locally"
        assert best_topic_id(text) == "open_weights"

    def test_a_brand_name_alone_does_not_tag(self):
        """The 31-Oct-2026 re-audit's central change.

        Scoring a brand name weak stopped it outvoting a topic that matched on
        substance, but did nothing where no other topic matched at all: 68 of
        Model Releases' 88 tags over the following 60 days were still decided
        by a brand name alone — "Mistral raises EUR 3B", "Claude partial
        outage", "anthropic-sdk-python v2.3.0 released". A vendor's name is
        now a filter term only.
        """
        assert best_topic_id("Claude Duet") == ""
        assert best_topic_id("Mistral raises EUR 3B") == ""
        assert best_topic_id("Swedish government offices to ban Claude") == ""

    def test_a_versioned_model_name_in_the_title_tags(self):
        """...unless the title names a version, which is what a release is."""
        assert best_topic_id("claude haiku 5.5", None, "Claude Haiku 5.5") == (
            "model_releases"
        )
        assert best_topic_id("mistral large 4", None, "Mistral Large 4") == (
            "model_releases"
        )
        # A codename rather than a number works too.
        assert best_topic_id(
            "bringing gpt-rosalind to academic labs",
            None,
            "Bringing GPT-Rosalind to academic research labs",
        ) == "model_releases"

    def test_a_client_library_version_is_not_a_model_version(self):
        """The release notes under an SDK bump name every model it supports."""
        for title in (
            "llama.cpp v0.8.0 released",
            "anthropic-sdk-python v2.3.0 released",
            "python-genai v2.33.0 released",
        ):
            assert not names_a_model_version(title), title

    def test_the_title_decides_not_the_summary(self):
        """A versioned model named only in the body is a mention, not news."""
        body = "claude haiku 5.5 is mentioned here"
        assert best_topic_id(body, None, "Our quarterly infrastructure update") == ""

    def test_promotion_is_scoped_to_model_releases(self):
        """Other topics' weak keywords may still tag on their own.

        "Claude Code" and "Codex" name agent tooling whatever else the
        sentence is about, so they are not subject to the brand-name rule.
        """
        title = "Backdoor in Claude Code for VS Code extension"
        assert best_topic_id(title.lower(), None, title) == "agents_tooling"

    def test_more_matches_win_over_fewer(self):
        text = "Our coding agent now supports tool use and agent skills on GPT-6"
        assert best_topic_id(text) == "agents_tooling"

    def test_longer_keyword_breaks_a_tie(self):
        # One strong keyword each: "benchmark" (9) against "computer use" (12).
        text = "A computer use benchmark"
        assert best_topic_id(text) == "agents_tooling"

    def test_list_order_breaks_a_remaining_tie(self):
        """Equal score and equal specificity keeps the table's order."""
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
