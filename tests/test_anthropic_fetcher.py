"""Unit tests for the Anthropic listing fetcher.

Every test builds its own page. Nothing here reaches anthropic.com: the
fetcher tests that did reach the network turned red on master for two days in
October when an upstream feed changed, in a file nobody had touched.
"""

import json
from unittest.mock import Mock, patch

from src.fetchers.anthropic_fetcher import (
    _decoded_payloads,
    _posts_in,
    fetch_anthropic_posts,
)


def _post(slug, title, published, summary="A summary."):
    return {
        "_type": "post",
        "title": title,
        "summary": summary,
        "publishedOn": published,
        "slug": {"_type": "slug", "current": slug},
    }


def _streamed_page(posts):
    """A listing page shaped like the real one: posts inside a pushed string."""
    payload = json.dumps({"posts": posts})
    # The page holds the payload escaped once over, as a JSON string literal.
    return (
        "<!DOCTYPE html><html><body>"
        f"<script>self.__next_f.push([1,{json.dumps(payload)}])</script>"
        "</body></html>"
    )


def _inline_page(posts):
    """The same payload embedded unescaped, as __NEXT_DATA__ used to be."""
    return (
        "<!DOCTYPE html><html><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps({"posts": posts})}</script>'
        "</body></html>"
    )


class TestReadingThePayload:
    """The posts are read from the page's content payload, not its markup."""

    def test_reads_posts_from_a_streamed_page(self):
        page = _streamed_page([_post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z")])
        posts = [p for text in _decoded_payloads(page) for p in _posts_in(text)]
        assert [p["title"] for p in posts] == ["Introducing Claude 6"]

    def test_reads_posts_from_an_unescaped_payload(self):
        """Where the payload lives is not the contract; carrying posts is."""
        page = _inline_page([_post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z")])
        posts = [p for text in _decoded_payloads(page) for p in _posts_in(text)]
        assert [p["title"] for p in posts] == ["Introducing Claude 6"]

    def test_an_object_without_a_slug_is_not_a_post(self):
        """publishedOn alone appears on the site's other content types."""
        page = _inline_page([{"_type": "banner", "publishedOn": "2026-10-15", "title": "Banner"}])
        assert [p for text in _decoded_payloads(page) for p in _posts_in(text)] == []

    def test_a_broken_string_literal_does_not_raise(self):
        page = '<script>self.__next_f.push([1,"{\\"posts\\": [}"])</script>'
        assert _posts_in(_decoded_payloads(page)[0]) == []


class TestItemsHandedToTheDigest:
    def _fetch(self, news_posts, engineering_posts, **kwargs):
        pages = {
            "https://www.anthropic.com/news": _streamed_page(news_posts),
            "https://www.anthropic.com/engineering": _streamed_page(engineering_posts),
        }

        def get(url, **_):
            response = Mock()
            response.text = pages[url]
            response.raise_for_status = Mock()
            return response

        with patch("src.fetchers.anthropic_fetcher.requests.get", side_effect=get):
            return fetch_anthropic_posts(**kwargs)

    def test_each_listing_gets_its_own_source_and_url_prefix(self):
        items = self._fetch(
            [_post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z")],
            [_post("source-control", "Redesigning source control", "2026-10-13")],
        )
        by_source = {i["source"]: i for i in items}

        assert by_source["Anthropic"]["url"] == "https://www.anthropic.com/news/claude-6"
        assert (
            by_source["Anthropic Engineering"]["url"]
            == "https://www.anthropic.com/engineering/source-control"
        )

    def test_the_item_carries_what_the_ranker_screens_on(self):
        items = self._fetch(
            [_post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z", "Cheaper and faster.")],
            [],
        )
        assert items[0]["title"] == "Introducing Claude 6"
        assert items[0]["summary"] == "Cheaper and faster."
        assert items[0]["published"] == "2026-10-15T17:20:00.000Z"
        assert items[0]["type"] == "announcement"

    def test_a_bare_date_is_passed_through_as_published(self):
        """/engineering gives a date with no time; fetcher._parse_published reads it."""
        items = self._fetch([], [_post("source-control", "Redesigning source control", "2026-10-13")])
        assert items[0]["published"] == "2026-10-13"

    def test_a_title_with_stray_whitespace_is_trimmed(self):
        """Real engineering titles arrive with a leading space."""
        items = self._fetch([], [_post("source-control", " Redesigning source control", "2026-10-13")])
        assert items[0]["title"] == "Redesigning source control"

    def test_the_same_post_appearing_twice_becomes_one_item(self):
        """A post is in the payload once per card that renders it."""
        post = _post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z")
        items = self._fetch([post, dict(post)], [])
        assert len(items) == 1

    def test_the_newest_posts_are_kept_when_capped(self):
        """The news listing embeds its whole archive, 276 posts deep."""
        items = self._fetch(
            [
                _post("old", "Old post", "2024-01-01T00:00:00.000Z"),
                _post("newest", "Newest post", "2026-10-15T17:20:00.000Z"),
                _post("middle", "Middle post", "2025-06-01T00:00:00.000Z"),
            ],
            [],
            max_items=2,
        )
        assert [i["title"] for i in items] == ["Newest post", "Middle post"]

    def test_a_post_missing_a_title_is_skipped(self):
        items = self._fetch(
            [
                {"publishedOn": "2026-10-15T17:20:00.000Z", "slug": {"current": "untitled"}},
                _post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z"),
            ],
            [],
        )
        assert [i["title"] for i in items] == ["Introducing Claude 6"]


class TestFailingSoftly:
    """A redesign should cost Anthropic coverage for a day, not the digest."""

    def test_a_shape_change_yields_no_items_and_warns(self):
        response = Mock()
        response.text = "<html><body><p>Nothing here looks like a post.</p></body></html>"
        response.raise_for_status = Mock()

        logger = Mock()
        with patch("src.fetchers.anthropic_fetcher.requests.get", return_value=response), patch(
            "src.fetchers.anthropic_fetcher.logger", logger
        ):
            assert fetch_anthropic_posts() == []

        warned = " ".join(str(call.args[0]) for call in logger.warning.call_args_list)
        assert "page shape may have changed" in warned

    def test_one_listing_failing_leaves_the_other_one_fetched(self):
        page = _streamed_page([_post("claude-6", "Introducing Claude 6", "2026-10-15T17:20:00.000Z")])

        def get(url, **_):
            if url.endswith("/engineering"):
                raise RuntimeError("down")
            response = Mock()
            response.text = page
            response.raise_for_status = Mock()
            return response

        with patch("src.fetchers.anthropic_fetcher.requests.get", side_effect=get):
            items = fetch_anthropic_posts()

        assert [i["source"] for i in items] == ["Anthropic"]
