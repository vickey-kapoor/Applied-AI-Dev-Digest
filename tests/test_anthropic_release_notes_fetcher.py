"""Unit tests for the Anthropic platform release notes fetcher."""

from unittest.mock import MagicMock, patch

from src.constants import (
    ANTHROPIC_RELEASE_NOTES_SOURCE,
    ANTHROPIC_RELEASE_NOTES_URL,
)
from src.fetchers.anthropic_release_notes_fetcher import (
    fetch_anthropic_release_notes,
    parse_release_notes,
)

# Markup shaped like the live page: a dated h3 carrying its own anchor id, a
# list whose every item is one change, and the icon font's private-use glyph
# trailing the heading text — which is on the real page and matched no date at
# all until it was stripped.
PAGE = """
<html><body>
<nav><ul><li>Release notes</li><li>Migration guides</li></ul></nav>
<h3 id="october-21-2026" class="group">October 21, 2026<span><button
   aria-label="Copy link to October 21, 2026"><span
   aria-hidden="true"></span></button></span></h3>
<ul>
  <li>We've released <a href="/docs/en/api/migration-2026-10-21">API version
      2026-10-21</a>. Migrating shows how to upgrade.</li>
  <li>The new SDK versions have breaking changes, and are licensed under
      Apache 2.0 instead of the MIT License. See
      <a href="/docs/en/api/migration-2026-10-21#sdk-changes">SDK changes</a>.</li>
  <li>Organization admins can now turn off web fetch.</li>
</ul>
<h3 id="june-20th-2024" class="group">June 20th, 2024</h3>
<ul>
  <li>An older change nobody needs today.</li>
</ul>
<h2>Was this page helpful?</h2>
<ul><li>Yes</li><li>No</li></ul>
</body></html>
"""


class TestParsing:
    def test_one_item_per_change_not_per_date(self):
        items = parse_release_notes(PAGE)
        assert len(items) == 4

    def test_items_are_newest_first(self):
        items = parse_release_notes(PAGE)
        assert [item["published"][:10] for item in items] == [
            "2026-10-21", "2026-10-21", "2026-10-21", "2024-06-20"
        ]

    def test_the_date_heading_sets_every_change_under_it(self):
        items = parse_release_notes(PAGE)
        assert items[0]["published"] == "2026-10-21T00:00:00+00:00"

    def test_an_ordinal_date_is_read(self):
        """The older entries write "June 20th, 2024"."""
        assert parse_release_notes(PAGE)[3]["published"][:10] == "2024-06-20"

    def test_the_icon_glyph_does_not_defeat_the_date(self):
        """The heading arrives as "October 21, 2026" from the icon font."""
        assert parse_release_notes(PAGE)[0]["published"][:10] == "2026-10-21"

    def test_the_title_is_the_opening_sentence(self):
        assert parse_release_notes(PAGE)[0]["title"] == (
            "We've released API version 2026-10-21."
        )

    def test_the_body_is_the_whole_change(self):
        item = parse_release_notes(PAGE)[1]
        assert "Apache 2.0 instead of the MIT License" in item["article_text"]

    def test_items_carry_the_schema_the_pipeline_expects(self):
        item = parse_release_notes(PAGE)[0]
        assert item["source"] == ANTHROPIC_RELEASE_NOTES_SOURCE
        assert item["type"] == "changelog"
        assert item["summary"]
        assert item["article_text"]

    def test_the_source_is_not_named_anthropic(self):
        """Sharing the news listing's name would make them fight for its slots."""
        assert parse_release_notes(PAGE)[0]["source"] != "Anthropic"

    def test_navigation_above_the_first_date_is_not_a_change(self):
        titles = [item["title"] for item in parse_release_notes(PAGE)]
        assert "Release notes" not in titles
        assert "Migration guides" not in titles

    def test_a_heading_that_is_not_a_date_closes_the_section(self):
        """Otherwise the page footer's list is filed under the oldest release."""
        titles = [item["title"] for item in parse_release_notes(PAGE)]
        assert "Yes" not in titles
        assert "No" not in titles

    def test_markup_with_no_release_notes_yields_nothing(self):
        assert parse_release_notes("<html><body><p>Nothing here.</p></body></html>") == []

    def test_an_impossible_date_is_dropped(self):
        bad = """
        <h3 id="february-31-2026">February 31, 2026</h3>
        <ul><li>The thirty-first of February.</li></ul>
        """
        assert parse_release_notes(bad) == []

    def test_an_empty_list_item_is_not_a_change(self):
        page = """
        <h3 id="october-21-2026">October 21, 2026</h3>
        <ul><li>  </li><li>A real change.</li></ul>
        """
        assert [item["title"] for item in parse_release_notes(page)] == ["A real change."]


class TestEntryLinks:
    def test_a_change_links_to_the_page_its_text_links_to(self):
        assert parse_release_notes(PAGE)[0]["url"] == (
            "https://platform.claude.com/docs/en/api/migration-2026-10-21"
        )

    def test_a_relative_link_resolves_against_the_url_the_page_came_from(self):
        item = parse_release_notes(PAGE, "https://docs.claude.com/en/release-notes/api")[0]
        assert item["url"] == "https://docs.claude.com/docs/en/api/migration-2026-10-21"

    def test_a_change_with_no_link_falls_back_to_the_dates_permalink(self):
        item = parse_release_notes(PAGE)[2]
        assert item["url"] == f"{ANTHROPIC_RELEASE_NOTES_URL}#october-21-2026"

    def test_an_absolute_link_is_left_alone(self):
        page = """
        <h3 id="october-21-2026">October 21, 2026</h3>
        <ul><li>See <a href="https://github.com/anthropics/anthropic-sdk-python">the
        SDK</a>.</li></ul>
        """
        assert parse_release_notes(page)[0]["url"] == (
            "https://github.com/anthropics/anthropic-sdk-python"
        )

    def test_an_in_page_anchor_is_not_a_source_link(self):
        page = """
        <h3 id="october-21-2026">October 21, 2026</h3>
        <ul><li>Jump <a href="#top">up</a>.</li></ul>
        """
        assert parse_release_notes(page)[0]["url"] == (
            f"{ANTHROPIC_RELEASE_NOTES_URL}#october-21-2026"
        )

    def test_a_non_http_scheme_is_not_a_source_link(self):
        page = """
        <h3 id="october-21-2026">October 21, 2026</h3>
        <ul><li>Write to <a href="mailto:support@anthropic.com">us</a>.</li></ul>
        """
        assert parse_release_notes(page)[0]["url"] == (
            f"{ANTHROPIC_RELEASE_NOTES_URL}#october-21-2026"
        )

    def test_a_date_with_no_anchor_falls_back_to_the_page(self):
        page = """
        <h3>October 21, 2026</h3>
        <ul><li>A change on a heading with no id.</li></ul>
        """
        assert parse_release_notes(page)[0]["url"] == ANTHROPIC_RELEASE_NOTES_URL


class TestIdentity:
    """One page, changes that can share a link: identity is not the URL."""

    def test_every_change_has_its_own_identity(self):
        items = parse_release_notes(PAGE)
        assert len({item["identity"] for item in items}) == len(items)

    def test_two_changes_sharing_a_link_still_differ(self):
        page = """
        <h3 id="october-21-2026">October 21, 2026</h3>
        <ul>
          <li>First change. <a href="/docs/en/api/x">See x</a>.</li>
          <li>Second change. <a href="/docs/en/api/x">See x</a>.</li>
        </ul>
        """
        items = parse_release_notes(page)
        assert items[0]["url"] == items[1]["url"]
        assert items[0]["identity"] != items[1]["identity"]

    def test_identity_is_stable_across_runs(self):
        """An identity that changed per run would resend a change every day."""
        first = [item["identity"] for item in parse_release_notes(PAGE)]
        assert first == [item["identity"] for item in parse_release_notes(PAGE)]

    def test_identity_carries_the_date(self):
        assert parse_release_notes(PAGE)[0]["identity"].startswith(
            "anthropic-release-notes:2026-10-21:"
        )


class TestFetching:
    def _response(self, text: str, status: int = 200):
        r = MagicMock()
        r.status_code = status
        r.text = text
        r.url = "https://platform.claude.com/docs/en/release-notes/overview"
        r.raise_for_status = MagicMock()
        return r

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get")
    def test_returns_parsed_changes(self, mock_get):
        mock_get.return_value = self._response(PAGE)
        assert len(fetch_anthropic_release_notes()) == 4

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get")
    def test_respects_max_results(self, mock_get):
        mock_get.return_value = self._response(PAGE)
        assert len(fetch_anthropic_release_notes(max_results=2)) == 2

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get")
    def test_the_configured_url_is_fetched(self, mock_get):
        mock_get.return_value = self._response(PAGE)
        fetch_anthropic_release_notes()
        assert mock_get.call_args[0][0] == ANTHROPIC_RELEASE_NOTES_URL

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get")
    def test_links_resolve_against_the_landed_url(self, mock_get):
        """The configured docs URL redirects, and the links belong to the host
        it lands on."""
        response = self._response(PAGE)
        response.url = "https://platform.claude.com/docs/en/release-notes/overview"
        mock_get.return_value = response
        assert fetch_anthropic_release_notes()[0]["url"].startswith(
            "https://platform.claude.com/docs/en/api/"
        )

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get",
           side_effect=Exception("connection reset"))
    def test_a_network_failure_is_a_quiet_day_not_a_crash(self, mock_get):
        assert fetch_anthropic_release_notes() == []

    @patch("src.fetchers.anthropic_release_notes_fetcher.requests.get")
    def test_a_redesign_is_a_quiet_day_not_a_crash(self, mock_get):
        mock_get.return_value = self._response("<html><body>redesigned</body></html>")
        assert fetch_anthropic_release_notes() == []
