"""Unit tests for fetcher module (aggregation and deduplication)."""

from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import patch, MagicMock

from src.fetcher import (
    fetch_all,
    _deduplicate_by_identity,
    _filter_by_recency,
    _parse_published,
    _cap_per_source,
    _deduplicate_by_similarity,
    _is_same_story,
)


def _hours_ago(hours: float) -> str:
    """Timestamp N hours in the past, as the fetchers emit them.

    These aggregation tests use relative timestamps so the recency filter
    never drops their fixtures — a fixed date would silently rot the moment
    it aged past DIGEST_MAX_AGE_HOURS.
    """
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


class TestDeduplicationByIdentity:
    """Tests for identity-based deduplication, which is the URL by default."""

    def test_empty_list(self):
        assert _deduplicate_by_identity([]) == []

    def test_no_duplicates(self):
        items = [
            {"url": "https://a.com", "title": "A"},
            {"url": "https://b.com", "title": "B"},
        ]
        assert len(_deduplicate_by_identity(items)) == 2

    def test_removes_url_duplicates(self):
        items = [
            {"url": "https://a.com", "title": "First"},
            {"url": "https://a.com", "title": "Duplicate"},
        ]
        result = _deduplicate_by_identity(items)
        assert len(result) == 1
        assert result[0]["title"] == "First"

    def test_keeps_items_with_different_urls(self):
        items = [
            {"url": "https://a.com", "title": "A"},
            {"url": "https://b.com", "title": "B"},
        ]
        assert len(_deduplicate_by_identity(items)) == 2

    def test_items_without_url_kept(self):
        items = [
            {"title": "No URL"},
            {"url": "https://a.com", "title": "With URL"},
        ]
        assert len(_deduplicate_by_identity(items)) == 2

    def test_explicit_identity_overrides_a_shared_url(self):
        """OpenAI's changelog is one page holding every entry.

        Keying on the URL collapsed the whole source to a single item.
        """
        items = [
            {"url": "https://platform.openai.com/docs/changelog",
             "identity": "openai-changelog:2026-09-29:released-gpt-6-1-sol", "title": "Sol"},
            {"url": "https://platform.openai.com/docs/changelog",
             "identity": "openai-changelog:2026-09-25:fixed-image-encoding", "title": "Fix"},
        ]
        assert len(_deduplicate_by_identity(items)) == 2

    def test_a_repeated_identity_is_still_a_duplicate(self):
        items = [
            {"url": "https://a.example/one", "identity": "same", "title": "First"},
            {"url": "https://b.example/two", "identity": "same", "title": "Second"},
        ]
        result = _deduplicate_by_identity(items)
        assert len(result) == 1
        assert result[0]["title"] == "First"


class TestFetchAll:
    """Tests for the main fetch_all function.

    Every source fetch_all calls is mocked, including the ones a test does not
    care about. Two of them were left live when they were added, so these
    tests opened real connections and their assertions counted whatever the
    internet happened to be serving. They passed only while the OpenAI
    changelog had nothing published inside DIGEST_MAX_AGE_HOURS; entries on
    6 and 7 Oct 2026 turned every count assertion here red on master, in a
    file nobody had touched.
    """

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_aggregates_blog_sources(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.return_value = [
            {"title": "OpenAI Update", "url": "https://a.com", "published": _hours_ago(1)},
            {"title": "Anthropic Update", "url": "https://b.com", "published": _hours_ago(2)},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 2

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases")
    @patch("src.fetcher.fetch_blog_posts")
    def test_aggregates_all_sources(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.return_value = [
            {"title": "Blog Post", "url": "https://a.com", "published": _hours_ago(1)},
        ]
        mock_gh.return_value = [
            {"title": "transformers v4.40", "url": "https://github.com/x", "published": _hours_ago(1)},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 2

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_handles_source_failure(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.side_effect = Exception("API Error")
        result = fetch_all(max_results=10)
        assert len(result) == 0

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_deduplicates_by_url(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.return_value = [
            {"title": "Same URL A", "url": "https://same.com", "published": _hours_ago(1)},
            {"title": "Same URL B", "url": "https://same.com", "published": _hours_ago(2)},
        ]
        result = fetch_all(max_results=10)
        assert len(result) == 1

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_respects_max_results(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.return_value = [
            # Distinct sources: this test covers max_results, not the
            # per-source cap, which would otherwise trim a single-source batch.
            {
                "title": f"Post {i}",
                "url": f"https://a.com/{i}",
                "source": f"Lab {i}",
                "published": _hours_ago(i + 1),
            }
            for i in range(10)
        ]
        result = fetch_all(max_results=3)
        assert len(result) == 3

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_sorts_by_date(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        mock_blogs.return_value = [
            {"title": "Old", "url": "https://a.com", "published": _hours_ago(48)},
            {"title": "New", "url": "https://b.com", "published": _hours_ago(1)},
        ]
        result = fetch_all(max_results=10)
        assert result[0]["title"] == "New"
        assert result[1]["title"] == "Old"


class TestParsePublished:
    """Tests for timestamp normalization across the four source formats."""

    def test_parses_aware_offset(self):
        result = _parse_published("2026-08-24T06:30:07+00:00")
        assert result is not None and result.tzinfo is not None

    def test_parses_z_suffix(self):
        """GitHub and HF return trailing-Z timestamps."""
        result = _parse_published("2026-08-24T06:30:07Z")
        assert result is not None and result.tzinfo is not None

    def test_naive_is_treated_as_utc(self):
        """Blog feeds historically emitted naive strings; papers.json holds some."""
        result = _parse_published("2026-08-19T12:17:57")
        assert result is not None
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_unparseable_returns_none(self):
        assert _parse_published("not-a-date") is None
        assert _parse_published("") is None
        assert _parse_published(None) is None


class TestFilterByRecency:
    """Tests for the cutoff that keeps the daily digest daily."""

    def test_drops_items_older_than_window(self):
        items = [
            {"title": "recent", "published": _hours_ago(2)},
            {"title": "stale", "published": _hours_ago(200)},
        ]
        kept = [i["title"] for i in _filter_by_recency(items, 72)]
        assert kept == ["recent"]

    def test_mixed_naive_and_aware_does_not_raise(self):
        """The regression this guards: comparing naive to aware raises TypeError."""
        now = datetime.now(timezone.utc)
        items = [
            {"title": "aware", "published": (now - timedelta(hours=2)).isoformat()},
            {"title": "naive", "published": (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()},
            {"title": "naive old", "published": (now - timedelta(days=9)).replace(tzinfo=None).isoformat()},
        ]
        kept = [i["title"] for i in _filter_by_recency(items, 72)]
        assert kept == ["aware", "naive"]

    def test_unparseable_dates_are_kept(self):
        """Fail open: a bad timestamp must not silently empty the digest."""
        items = [
            {"title": "garbage", "published": "not-a-date"},
            {"title": "missing", "published": ""},
            {"title": "absent"},
        ]
        kept = [i["title"] for i in _filter_by_recency(items, 72)]
        assert kept == ["garbage", "missing", "absent"]

    def test_boundary_item_just_inside_window_is_kept(self):
        items = [{"title": "edge", "published": _hours_ago(71.5)}]
        assert len(_filter_by_recency(items, 72)) == 1

    def test_zero_disables_the_filter(self):
        items = [{"title": "ancient", "published": _hours_ago(10_000)}]
        assert len(_filter_by_recency(items, 0)) == 1

    @patch("src.fetcher.fetch_openai_changelog", return_value=[])
    @patch("src.fetcher.fetch_huggingface_papers", return_value=[])
    @patch("src.fetcher.fetch_hackernews_stories", return_value=[])
    @patch("src.fetcher.fetch_github_releases", return_value=[])
    @patch("src.fetcher.fetch_blog_posts")
    def test_fetch_all_applies_the_cutoff(self, mock_blogs, mock_gh, mock_hn, mock_hf, mock_changelog):
        """A week-old blog post must not reach the daily pick."""
        mock_blogs.return_value = [
            {"title": "Today", "url": "https://a.com", "published": _hours_ago(3)},
            {"title": "Last week", "url": "https://b.com", "published": _hours_ago(24 * 8)},
        ]
        result = fetch_all(max_results=10)
        assert [r["title"] for r in result] == ["Today"]


class TestCapPerSource:
    """Tests for the per-source cap that stops one feed crowding the pool."""

    def test_caps_each_source(self):
        items = [{"source": "Vendor", "title": f"p{i}"} for i in range(5)]
        assert len(_cap_per_source(items, 2)) == 2

    def test_other_sources_unaffected(self):
        items = [
            {"source": "Vendor", "title": "a"},
            {"source": "Vendor", "title": "b"},
            {"source": "Vendor", "title": "c"},
            {"source": "OpenAI", "title": "launch"},
        ]
        kept = _cap_per_source(items, 2)
        assert [i["title"] for i in kept] == ["a", "b", "launch"]

    def test_keeps_freshest_per_source(self):
        """Input is sorted newest-first, so the cap must keep the leading items."""
        items = [
            {"source": "Vendor", "title": "newest"},
            {"source": "Vendor", "title": "middle"},
            {"source": "Vendor", "title": "oldest"},
        ]
        assert [i["title"] for i in _cap_per_source(items, 2)] == ["newest", "middle"]

    def test_zero_disables_the_cap(self):
        items = [{"source": "Vendor", "title": f"p{i}"} for i in range(5)]
        assert len(_cap_per_source(items, 0)) == 5

    def test_real_28_aug_pool_frees_slots_for_labs(self):
        """Regression: one vendor blog held 4 of 10 slots and won the pick."""
        pool = (
            [{"source": "AWS Machine Learning", "title": f"aws{i}"} for i in range(4)]
            + [{"source": "Google DeepMind", "title": "evals"}]
            + [{"source": "OpenAI", "title": "incident"}]
        )
        kept = _cap_per_source(pool, 2)
        aws = [i for i in kept if i["source"] == "AWS Machine Learning"]
        assert len(aws) == 2
        assert {"evals", "incident"}.issubset({i["title"] for i in kept})


def _item(source: str, title: str) -> dict:
    return {"source": source, "title": title, "url": f"https://example.com/{abs(hash(title))}"}


class TestSimilarityDeduplication:
    """One launch arriving from several sources should compete once, not thrice.

    Every case below is drawn from titles actually observed in papers.json.
    The false positives matter more than the true one: a wrong merge silently
    drops a real launch, and the highest-scoring real pair (0.97) is a pair of
    *distinct* SDK releases.
    """

    THRESHOLD = 0.85

    @pytest.mark.parametrize("a,b,why", [
        (_item("GitHub", "anthropic-sdk-python v1.3.0 released"),
         _item("GitHub", "anthropic-sdk-python v1.2.0 released"),
         "distinct SDK releases scoring 0.97"),
        (_item("Hacker News", "GLM-5.3 Artificial Analysis Benchmarks"),
         _item("Hacker News", "GLM 5.2 Performance Benchmarks"),
         "distinct models"),
        (_item("OpenAI", "Introducing GeneBench-Pro"),
         _item("PyTorch", "Introducing AutoSP"),
         "unrelated, sharing only a common prefix"),
        (_item("Hacker News", "Claude Opus 5.1 released"),
         _item("Anthropic", "Claude Opus 5.2 released"),
         "cross-source but different versions"),
    ])
    def test_does_not_merge_distinct_items(self, a, b, why):
        assert _is_same_story(a, b, self.THRESHOLD) is False, why

    def test_merges_same_story_across_sources(self):
        a = _item("AI Alignment Forum", "Predicting LLM Safety Before Release by Simulating Deployment")
        b = _item("OpenAI", "Predicting model behavior before release by simulating deployment")
        assert _is_same_story(a, b, self.THRESHOLD) is True

    def test_never_merges_within_one_source(self):
        """Same-source pairs are where every observed false positive lived."""
        a = _item("OpenAI", "Introducing our new frontier model")
        b = _item("OpenAI", "Introducing our new frontier model")
        assert _is_same_story(a, b, self.THRESHOLD) is False

    def test_keeps_the_labs_own_post_over_coverage(self):
        title = "Predicting model behavior before release by simulating deployment"
        kept = _deduplicate_by_similarity(
            [_item("Hacker News", title), _item("OpenAI", title)], self.THRESHOLD
        )
        assert len(kept) == 1
        assert kept[0]["source"] == "OpenAI"

    def test_keeps_the_labs_own_post_regardless_of_order(self):
        title = "Predicting model behavior before release by simulating deployment"
        kept = _deduplicate_by_similarity(
            [_item("OpenAI", title), _item("Hacker News", title)], self.THRESHOLD
        )
        assert len(kept) == 1
        assert kept[0]["source"] == "OpenAI"

    def test_zero_threshold_disables_merging(self):
        title = "Predicting model behavior before release by simulating deployment"
        items = [_item("Hacker News", title), _item("OpenAI", title)]
        assert len(_deduplicate_by_similarity(items, 0)) == 2

    def test_empty_titles_are_never_merged(self):
        assert _is_same_story(_item("A", ""), _item("B", ""), self.THRESHOLD) is False

    def test_unrelated_items_all_survive(self):
        items = [
            _item("Hacker News", "Gemini-3.5-Transcribe"),
            _item("Google DeepMind", "Piloting double-blind AI evaluations"),
            _item("OpenAI", "The Hugging Face incident and the road ahead"),
        ]
        assert len(_deduplicate_by_similarity(items, self.THRESHOLD)) == 3
