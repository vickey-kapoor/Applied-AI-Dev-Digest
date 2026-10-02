"""Tests for the OpenAI changelog fetcher.

This exists because openai.com/index/* answers 403 with `cf-mitigated:
challenge` to every non-browser client, and the RSS feed behind those URLs
carries only each page's ~150-character meta description. Measured on a live
pool, the two OpenAI items reached the summarizer with 148 and 152 characters
while the other nine sources gave 2,780 to 12,000.

The changelog is scraped, not fed, so two properties matter more than the happy
path: a shape change must yield zero entries rather than an exception, and every
entry must get an identity of its own despite sharing one URL with all the
others.
"""

from unittest.mock import MagicMock, patch

from src.constants import OPENAI_CHANGELOG_SOURCE, OPENAI_CHANGELOG_URL
from src.fetchers.openai_changelog_fetcher import (
    _first_sentence,
    fetch_openai_changelog,
    parse_changelog,
)

# Markup shaped exactly like the live page: hashed class names, a month heading
# supplying the year, an outline badge carrying the day, soft badges for the
# change type and the affected models, and the body in a markdown container.
PAGE = """
<html><body>
<div class="mb-12">
  <h3 class="mt-0 mb-4 _ChangelogSectionTitle_pvkq8_43">September, 2026</h3>
  <div class="mt-5"><div class="grid grid-cols-[3rem_1fr] items-start gap-x-4 gap-y-2">
    <div><div class="_Badge_10t5o_1" data-color="secondary" data-size="md" data-variant="outline">Sep 29</div></div>
    <div>
      <div class="flex flex-wrap gap-2 mb-2">
        <div class="_Badge_10t5o_1" data-variant="soft"><span class="capitalize">Feature</span></div>
        <div class="_Badge_10t5o_1" data-variant="soft">gpt-6.1-sol</div>
        <div class="_Badge_10t5o_1" data-variant="soft">v1/responses</div>
      </div>
      <div class="_MarkdownContent_abpsh_1 _ChangelogMarkdown_pvkq8_19">
        <p>Released <a href="/api/docs/models/gpt-6.1-sol">GPT-6.1 Sol</a> (<code>gpt-6.1-sol</code>) for complex coding.</p>
        <p>Standard pricing per 1M tokens is $2 input, $0.10 cached input, and $10 output.</p>
      </div>
    </div>
  </div></div>
  <div class="mt-5"><div class="grid grid-cols-[3rem_1fr] items-start gap-x-4 gap-y-2">
    <div><div class="_Badge_10t5o_1" data-variant="outline">Sep 25</div></div>
    <div>
      <div class="flex flex-wrap gap-2 mb-2">
        <div class="_Badge_10t5o_1" data-variant="soft"><span class="capitalize">Fix</span></div>
        <div class="_Badge_10t5o_1" data-variant="soft">gpt-6-sol</div>
      </div>
      <div class="_MarkdownContent_abpsh_1 _ChangelogMarkdown_pvkq8_19">
        <p>Fixed a bug in image encoding that degraded image understanding.</p>
        <p>We recommend rerunning your evaluations &amp; retrying affected workflows.</p>
      </div>
    </div>
  </div></div>
</div>
<div class="mb-12">
  <h3 class="_ChangelogSectionTitle_pvkq8_43">December, 2025</h3>
  <div class="mt-5"><div class="grid">
    <div><div class="_Badge_10t5o_1" data-variant="outline">Dec 3</div></div>
    <div><div class="_ChangelogMarkdown_pvkq8_19"><p>Added an older thing nobody needs today.</p></div></div>
  </div></div>
</div>
</body></html>
"""


class TestParsing:
    def test_finds_every_dated_entry(self):
        items = parse_changelog(PAGE)
        assert len(items) == 3

    def test_orders_newest_first(self):
        published = [item["published"] for item in parse_changelog(PAGE)]
        assert published == sorted(published, reverse=True)

    def test_dates_combine_the_day_badge_with_the_month_heading(self):
        """The badge says "Sep 29" and carries no year; the heading has it."""
        items = parse_changelog(PAGE)
        assert items[0]["published"].startswith("2026-09-29")
        assert items[1]["published"].startswith("2026-09-25")
        # And the year rolls back with the heading rather than sticking at 2026.
        assert items[2]["published"].startswith("2025-12-03")

    def test_body_is_the_whole_entry_not_a_teaser(self):
        """The point of the fetcher: real text, where the news feed gave 150 chars."""
        body = parse_changelog(PAGE)[0]["article_text"]
        assert "Released GPT-6.1 Sol" in body
        assert "$0.10 cached input" in body

    def test_paragraphs_stay_separated(self):
        assert "\n" in parse_changelog(PAGE)[0]["article_text"]

    def test_inline_markup_does_not_split_a_sentence(self):
        """<a> and <code> inside a paragraph must not fragment it."""
        assert "(gpt-6.1-sol) for complex coding" in parse_changelog(PAGE)[0]["article_text"]

    def test_entities_are_decoded(self):
        assert "evaluations & retrying" in parse_changelog(PAGE)[1]["article_text"]

    def test_change_type_and_affected_models_reach_the_summarizer(self):
        """The badges are the most actionable thing on the page for this reader."""
        body = parse_changelog(PAGE)[0]["article_text"]
        assert "Change type: Feature" in body
        assert "Affects: gpt-6.1-sol, v1/responses" in body

    def test_the_change_type_is_not_mistaken_for_an_affected_model(self):
        assert "Affects: Feature" not in parse_changelog(PAGE)[0]["article_text"]

    def test_badges_do_not_leak_from_one_entry_to_the_next(self):
        second = parse_changelog(PAGE)[1]["article_text"]
        assert "Change type: Fix" in second
        assert "gpt-6.1-sol" not in second

    def test_an_entry_without_badges_still_parses(self):
        third = parse_changelog(PAGE)[2]
        assert third["article_text"] == "Added an older thing nobody needs today."

    def test_title_is_the_opening_sentence(self):
        assert parse_changelog(PAGE)[1]["title"] == (
            "Fixed a bug in image encoding that degraded image understanding."
        )

    def test_items_carry_the_schema_the_pipeline_expects(self):
        item = parse_changelog(PAGE)[0]
        assert item["source"] == OPENAI_CHANGELOG_SOURCE
        assert item["url"] == OPENAI_CHANGELOG_URL
        assert item["type"] == "changelog"
        assert item["summary"]

    def test_the_source_is_not_named_openai(self):
        """Sharing the news blog's name would make them fight for its two slots."""
        assert parse_changelog(PAGE)[0]["source"] != "OpenAI"


class TestIdentity:
    """One page, no permalinks: identity cannot come from the URL."""

    def test_every_entry_shares_the_url(self):
        assert len({item["url"] for item in parse_changelog(PAGE)}) == 1

    def test_but_every_entry_has_its_own_identity(self):
        items = parse_changelog(PAGE)
        assert len({item["identity"] for item in items}) == len(items)

    def test_identity_is_stable_across_runs(self):
        """An identity that changed per run would resend an entry every day."""
        first = [item["identity"] for item in parse_changelog(PAGE)]
        second = [item["identity"] for item in parse_changelog(PAGE)]
        assert first == second

    def test_the_already_sent_filter_can_tell_entries_apart(self):
        from src.json_exporter import _paper_id_for_item
        ids = {_paper_id_for_item(item) for item in parse_changelog(PAGE)}
        assert len(ids) == 3


class TestDegradation:
    """A scraper outlives the page it scrapes only if it fails quietly."""

    def test_a_redesign_yields_no_entries_rather_than_an_exception(self):
        assert parse_changelog("<html><body><p>Everything moved.</p></body></html>") == []

    def test_empty_markup(self):
        assert parse_changelog("") == []

    def test_malformed_markup_does_not_raise(self):
        assert isinstance(parse_changelog('<div class="_ChangelogMarkdown_x"><p>unclosed'), list)

    def test_an_entry_with_no_month_heading_is_dropped_not_misdated(self):
        """Without a year there is no honest date, and the recency filter
        keeps undated items — so guessing here would surface 2023 entries."""
        orphan = """
        <div class="_Badge_1" data-variant="outline">Sep 29</div>
        <div class="_ChangelogMarkdown_1"><p>No heading above me.</p></div>
        """
        assert parse_changelog(orphan) == []

    def test_an_impossible_date_is_dropped(self):
        bad = """
        <h3 class="_ChangelogSectionTitle_1">February, 2026</h3>
        <div class="_Badge_1" data-variant="outline">Feb 31</div>
        <div class="_ChangelogMarkdown_1"><p>The thirty-first of February.</p></div>
        """
        assert parse_changelog(bad) == []


class TestFetching:
    def _response(self, text: str, status: int = 200):
        r = MagicMock()
        r.status_code = status
        r.text = text
        r.raise_for_status = MagicMock()
        return r

    @patch("src.fetchers.openai_changelog_fetcher.requests.get")
    def test_returns_parsed_entries(self, mock_get):
        mock_get.return_value = self._response(PAGE)
        assert len(fetch_openai_changelog()) == 3

    @patch("src.fetchers.openai_changelog_fetcher.requests.get")
    def test_respects_max_results(self, mock_get):
        mock_get.return_value = self._response(PAGE)
        assert len(fetch_openai_changelog(max_results=1)) == 1

    @patch("src.fetchers.openai_changelog_fetcher.requests.get",
           side_effect=Exception("connection reset"))
    def test_a_network_failure_is_a_quiet_day_not_a_crash(self, mock_get):
        assert fetch_openai_changelog() == []

    @patch("src.fetchers.openai_changelog_fetcher.requests.get")
    def test_an_http_error_is_a_quiet_day(self, mock_get):
        response = self._response("", status=503)
        response.raise_for_status.side_effect = Exception("503")
        mock_get.return_value = response
        assert fetch_openai_changelog() == []

    @patch("src.fetchers.openai_changelog_fetcher.requests.get")
    def test_zero_entries_is_warned_about_not_swallowed(self, mock_get):
        """Zero entries from a scraped page means a redesign far more often
        than it means a quiet month, so it must be visible in the logs.

        Captured with a handler on the module's own logger rather than caplog:
        src.logger sets propagate = False, so nothing reaches root.
        """
        import logging
        from src.fetchers import openai_changelog_fetcher as module

        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Capture(level=logging.WARNING)
        module.logger.addHandler(handler)
        try:
            mock_get.return_value = self._response("<html><body>moved</body></html>")
            assert fetch_openai_changelog() == []
        finally:
            module.logger.removeHandler(handler)

        assert any("page shape may have changed" in r.getMessage() for r in records)


class TestFirstSentence:
    def test_splits_on_the_first_full_stop(self):
        assert _first_sentence("One thing. Two thing.") == "One thing."

    def test_truncates_on_a_word_boundary(self):
        long = "Released " + "a very long model name " * 20 + "."
        title = _first_sentence(long)
        assert len(title) <= 121
        assert "  " not in title
        assert not title.rstrip("…").endswith(" ")

    def test_empty_input(self):
        assert _first_sentence("") == ""


class TestIntegrationWithTheFunnel:
    def test_the_changelog_is_exempt_from_the_keyword_gate(self):
        """A pricing change names no topic keyword and must still get through."""
        from src.fetcher import CURATED_SOURCES
        assert OPENAI_CHANGELOG_SOURCE in CURATED_SOURCES

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.export_papers")
    @patch("main.summarize_release", side_effect=lambda item, key: item)
    @patch("main.fetch_article_text", return_value="the whole changelog page" * 500)
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api"])
    @patch("main.is_paused", return_value=False)
    def test_main_does_not_refetch_an_item_that_brought_its_own_text(
        self, _paused, _keywords, _stats, mock_fetch_all, mock_rank, mock_fetch_article,
        mock_summarize, _papers, _pdf, _format, _send, _digest, env_vars,
    ):
        """Opening the changelog URL would replace one entry with all 174 of them."""
        import main as main_module

        entry = parse_changelog(PAGE)[0]
        mock_fetch_all.return_value = [entry]
        mock_rank.return_value = [entry]

        main_module.main()

        mock_fetch_article.assert_not_called()
        summarized = mock_summarize.call_args[0][0]
        assert summarized["article_text"] == entry["article_text"]

    @patch("main.export_digest")
    @patch("main.send_telegram_message")
    @patch("main.format_digest_message")
    @patch("main.generate_digest_pdf")
    @patch("main.export_papers")
    @patch("main.summarize_release", side_effect=lambda item, key: item)
    @patch("main.fetch_article_text", return_value="a real article body")
    @patch("main.rank_news_ranked")
    @patch("main.fetch_all")
    @patch("main.increment_topic_stat")
    @patch("main.get_active_keywords", return_value=["api"])
    @patch("main.is_paused", return_value=False)
    def test_main_still_opens_the_link_for_an_ordinary_feed_item(
        self, _paused, _keywords, _stats, mock_fetch_all, mock_rank, mock_fetch_article,
        mock_summarize, _papers, _pdf, _format, _send, _digest, env_vars,
    ):
        """The guard must not switch article fetching off for everything else."""
        import main as main_module

        item = {"title": "Introducing SynthID Bio", "url": "https://deepmind.google/x",
                "source": "Google DeepMind", "summary": "teaser"}
        mock_fetch_all.return_value = [item]
        mock_rank.return_value = [item]

        main_module.main()

        mock_fetch_article.assert_called_once_with("https://deepmind.google/x")
        assert mock_summarize.call_args[0][0]["article_text"] == "a real article body"


class TestExportRoundTrip:
    """papers.json rows must hash back to the identity they were saved under.

    They did not: the saved row carried no identity field, so every changelog
    row read back as "url:.../docs/changelog". The identity index collapsed to a
    single entry and only the title index stopped a re-fetch inside the 72-hour
    recency window from appending the same entry a second time.
    """

    def _export(self, tmp_path, items, ranked=None):
        from src import json_exporter
        with patch.object(json_exporter, "DATA_DIR", str(tmp_path)):
            return json_exporter.export_papers(items, ranked)

    def _rows(self, tmp_path):
        import json
        return json.loads((tmp_path / "papers.json").read_text())["papers"]

    def test_a_saved_row_keeps_its_identity(self, tmp_path):
        from src.json_exporter import _paper_identity
        item = parse_changelog(PAGE)[0]
        self._export(tmp_path, [item])
        saved = self._rows(tmp_path)[0]
        assert _paper_identity(saved) == _paper_identity(item)

    def test_re_exporting_the_same_entry_adds_no_second_row(self, tmp_path):
        """Entries stay in the recency window for days, so this happens daily."""
        items = parse_changelog(PAGE)
        self._export(tmp_path, items)
        self._export(tmp_path, items)
        assert len(self._rows(tmp_path)) == 3

    def test_every_entry_gets_its_own_row(self, tmp_path):
        self._export(tmp_path, parse_changelog(PAGE))
        rows = self._rows(tmp_path)
        assert len(rows) == 3
        assert len({row["id"] for row in rows}) == 3

    def test_the_identity_index_alone_catches_a_re_export(self, tmp_path):
        """With the titles changed, only the identity index can match — which
        is the index that was broken."""
        first = parse_changelog(PAGE)
        self._export(tmp_path, first)
        renamed = [{**item, "title": f"Reworded {n}"} for n, item in enumerate(first)]
        self._export(tmp_path, renamed)
        assert len(self._rows(tmp_path)) == 3

    def test_items_without_an_identity_do_not_gain_the_field(self, tmp_path):
        """An ordinary feed item is still keyed on its URL."""
        self._export(tmp_path, [{
            "title": "Introducing SynthID Bio",
            "url": "https://deepmind.google/discover/blog/synthid-bio",
            "source": "Google DeepMind",
        }])
        assert "identity" not in self._rows(tmp_path)[0]
