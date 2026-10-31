"""Tests for the keyword gate, topic tagging and per-source caps in fetch_all.

These pin the behaviour the 28-Oct-2026 topics audit changed: tagging by best
fit rather than list position, the corporate-news blocklist applied to the open
sources as well as the lab feeds, and the tighter cap on an aggregator.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src import fetcher
from src.fetcher import _cap_per_source, fetch_all


def _now_iso(minutes_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _item(title: str, source: str, url: str = "", summary: str = "") -> dict:
    return {
        "title": title,
        "summary": summary,
        "url": url or f"https://example.com/{abs(hash(title))}",
        "source": source,
        "published": _now_iso(),
    }


class TestAggregatorCap:
    """Hacker News took 23 of 56 top picks between 29-Aug and 27-Oct-2026,
    more than any lab source, on a digest about what the labs ship. Two slots
    a day is how it got there."""

    def test_an_aggregator_gets_the_tighter_cap(self):
        items = [
            _item("HN one", "Hacker News"),
            _item("HN two", "Hacker News"),
            _item("HN three", "Hacker News"),
        ]
        with patch.object(fetcher, "AGGREGATOR_MAX_ITEMS", 1):
            kept = _cap_per_source(items, max_per_source=2)
        assert [i["title"] for i in kept] == ["HN one"]

    def test_a_lab_keeps_the_ordinary_cap(self):
        items = [
            _item("Lab one", "Google DeepMind"),
            _item("Lab two", "Google DeepMind"),
            _item("Lab three", "Google DeepMind"),
        ]
        with patch.object(fetcher, "AGGREGATOR_MAX_ITEMS", 1):
            kept = _cap_per_source(items, max_per_source=2)
        assert [i["title"] for i in kept] == ["Lab one", "Lab two"]

    def test_the_aggregator_cap_never_loosens_the_general_one(self):
        """Set above MAX_ITEMS_PER_SOURCE it must not become a raise."""
        items = [_item(f"HN {n}", "Hacker News") for n in range(5)]
        with patch.object(fetcher, "AGGREGATOR_MAX_ITEMS", 4):
            kept = _cap_per_source(items, max_per_source=2)
        assert len(kept) == 2


class TestGateAndTagging:
    """fetch_all's keyword gate, with every fetcher but one stubbed out."""

    def _run(self, items, keywords):
        stub = {
            "fetch_blog_posts": lambda **kwargs: items,
            "fetch_github_releases": lambda: [],
            "fetch_hackernews_stories": lambda **kwargs: [],
            "fetch_huggingface_papers": lambda **kwargs: [],
            "fetch_openai_changelog": lambda: [],
            "fetch_anthropic_posts": lambda: [],
            "fetch_anthropic_release_notes": lambda: [],
        }
        with patch.multiple(fetcher, **{k: v for k, v in stub.items()}):
            return fetch_all(max_results=20, filter_keywords=keywords)

    def test_an_open_source_item_needs_a_keyword(self):
        results = self._run(
            [
                _item("StreetComplete on iOS is now in public beta", "Hacker News"),
                _item("Gemini 4 is here", "Hacker News"),
            ],
            ["Gemini"],
        )
        assert [r["title"] for r in results] == ["Gemini 4 is here"]

    def test_a_lab_feed_item_needs_no_keyword(self):
        """Being on a frontier lab's own blog is the relevance signal."""
        results = self._run([_item("Introducing SynthID Bio", "Google DeepMind")], ["Gemini"])
        assert [r["title"] for r in results] == ["Introducing SynthID Bio"]

    def test_corporate_news_is_excluded_from_an_open_source(self):
        """Hacker News voted this onto the front page, where the keyword
        "Claude" was enough to admit it."""
        results = self._run(
            [_item("Anthropic lawsuit over Claude training data", "Hacker News")],
            ["Claude"],
        )
        assert results == []

    def test_tagging_prefers_the_best_fit_over_list_order(self):
        results = self._run(
            [_item("Gemma, an open-weight model", "Google DeepMind")],
            ["Gemma"],
        )
        assert results[0]["topic_id"] == "open_weights"

    def test_a_brand_name_alone_admits_but_does_not_tag(self):
        """The gate still wants every brand name; tagging no longer does.

        The item reaches the digest — that is what the brand names are for —
        and goes out under its type's hashtag instead of #ModelRelease.
        """
        results = self._run([_item("Claude Duet", "Hacker News")], ["Claude"])
        assert len(results) == 1
        assert results[0].get("topic_id", "") == ""

    def test_a_versioned_model_name_tags_from_the_title(self):
        results = self._run([_item("Claude Haiku 5.5", "Hacker News")], ["Claude"])
        assert results[0]["topic_id"] == "model_releases"

    def test_an_item_matching_no_topic_is_kept_untagged(self):
        """A curated post that fits no topic is still a lab development."""
        results = self._run([_item("A note on our offices", "Mistral AI")], ["Claude"])
        assert results[0].get("topic_id", "") == ""


class TestHackerNewsNeedsKeywords:
    """The fetcher used to fall back to HN_KEYWORDS, a second keyword list
    that fetch_all never passed and that had quietly diverged from the topic
    config it shadowed."""

    def test_no_keywords_means_no_stories(self):
        from src.fetchers import hackernews_fetcher

        with patch.object(hackernews_fetcher, "_fetch_json") as mock_fetch:
            assert hackernews_fetcher.fetch_hackernews_stories([]) == []
            assert hackernews_fetcher.fetch_hackernews_stories(None) == []
            mock_fetch.assert_not_called()
