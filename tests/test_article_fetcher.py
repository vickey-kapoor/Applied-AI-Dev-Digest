"""Tests for article extraction.

The summarizer used to write five structured fields from a median of 273
characters of RSS teaser, and sometimes from nothing at all — the DeepMind post
announcing Gemini 4 Argon carried an empty summary, so the brief came from the
title alone. `availability` was a non-answer 39% of the time as a result.

Every failure here must return "" rather than raise, because the caller's
fallback is that same feed summary and a blog being down must not skip a day.
"""

from unittest.mock import MagicMock, patch

from src.article_fetcher import (
    MIN_USEFUL_CHARS,
    extract_text,
    fetch_article_text,
)

LONG = "This sentence carries enough words to count as a real paragraph of body text. "


def _page(body: str) -> str:
    return f"<html><head><title>t</title></head><body>{body}</body></html>"


class TestExtraction:
    def test_pulls_paragraph_text(self):
        text = extract_text(_page(f"<p>{LONG}</p><p>Second paragraph here now.</p>"))
        assert "real paragraph of body text" in text
        assert "Second paragraph here now." in text

    def test_drops_scripts_styles_and_furniture(self):
        markup = _page(
            "<nav>Home About Contact</nav>"
            "<script>var tracking = 1;</script>"
            "<style>.a{color:red}</style>"
            f"<p>{LONG}</p>"
            "<footer>Copyright notice here</footer>"
        )
        text = extract_text(markup)
        assert "real paragraph" in text
        for noise in ("tracking", "color:red", "Home About Contact", "Copyright notice"):
            assert noise not in text

    def test_prefers_article_container_over_page_chrome(self):
        """The scoped body is what removes most boilerplate on real sites."""
        markup = _page(
            "<p>Related posts you might enjoy reading next time around.</p>"
            f"<article><p>{LONG * 6}</p></article>"
            "<p>Subscribe to our newsletter for more updates weekly.</p>"
        )
        text = extract_text(markup)
        assert "real paragraph of body text" in text
        assert "Subscribe to our newsletter" not in text

    def test_falls_back_to_whole_page_when_nothing_is_marked_up(self):
        """Plenty of blogs mark up neither <article> nor <main>."""
        text = extract_text(_page(f"<div><p>{LONG * 6}</p></div>"))
        assert len(text) >= MIN_USEFUL_CHARS

    def test_unescapes_entities(self):
        text = extract_text(_page(f"<p>Context &amp; pricing are both stated. {LONG}</p>"))
        assert "Context & pricing" in text

    def test_single_word_fragments_are_dropped(self):
        """Icon labels and nav crumbs are single words and are never body text."""
        text = extract_text(_page("<p>Menu</p><p>Search</p>"))
        assert text == ""

    def test_malformed_markup_does_not_raise(self):
        assert isinstance(extract_text("<p>unclosed <div><span>" + LONG), str)

    def test_empty_markup_yields_empty_string(self):
        assert extract_text("") == ""


class TestFetching:
    def _response(self, body: str, status=200, content_type="text/html"):
        r = MagicMock()
        r.status_code = status
        r.headers = {"Content-Type": content_type}
        r.encoding = "utf-8"
        r.iter_content = lambda chunk_size=65536, decode_unicode=False: [body]
        r.__enter__ = lambda s: s
        r.__exit__ = MagicMock(return_value=False)
        return r

    @patch("src.article_fetcher._get")
    def test_returns_extracted_text(self, mock_get):
        mock_get.return_value = self._response(_page(f"<article><p>{LONG * 8}</p></article>"))
        assert "real paragraph of body text" in fetch_article_text("https://lab.example/post")

    @patch("src.article_fetcher._get")
    def test_non_200_falls_back(self, mock_get):
        """OpenAI's edge returns 403 to our user agent; that is a fallback, not a crash."""
        mock_get.return_value = self._response("<p>blocked</p>", status=403)
        assert fetch_article_text("https://openai.com/index/x") == ""

    @patch("src.article_fetcher._get")
    def test_non_html_falls_back(self, mock_get):
        mock_get.return_value = self._response("%PDF-1.4", content_type="application/pdf")
        assert fetch_article_text("https://lab.example/paper.pdf") == ""

    @patch("src.article_fetcher._get")
    def test_thin_extraction_falls_back(self, mock_get):
        """A cookie wall or JS shell parses fine but says nothing; prefer the feed."""
        mock_get.return_value = self._response(_page("<p>Accept all cookies please</p>"))
        assert fetch_article_text("https://lab.example/post") == ""

    @patch("src.article_fetcher._get", side_effect=Exception("connection reset"))
    def test_network_failure_falls_back(self, mock_get):
        assert fetch_article_text("https://lab.example/post") == ""

    def test_non_http_urls_are_not_fetched(self):
        for url in ("", "file:///etc/passwd", "ftp://host/x", "javascript:alert(1)"):
            assert fetch_article_text(url) == ""

    @patch("src.article_fetcher._get")
    def test_oversized_response_is_capped_not_streamed_forever(self, mock_get):
        r = MagicMock()
        r.status_code = 200
        r.headers = {"Content-Type": "text/html"}
        r.encoding = "utf-8"
        chunk = "<p>" + LONG * 200 + "</p>"
        # An endless body: the cap must stop the read.
        r.iter_content = lambda chunk_size=65536, decode_unicode=False: iter(lambda: chunk, None)
        r.__enter__ = lambda s: s
        r.__exit__ = MagicMock(return_value=False)
        mock_get.return_value = r

        text = fetch_article_text("https://lab.example/huge")
        from src.article_fetcher import MAX_ARTICLE_CHARS
        assert 0 < len(text) <= MAX_ARTICLE_CHARS


class TestSummarizerInput:
    """The summarizer must prefer the article and fall back to the feed."""

    def test_article_text_is_preferred(self):
        from src.news_summarizer import _prepare_inputs
        _, _, body = _prepare_inputs({
            "title": "T", "source": "S",
            "summary": "short feed teaser",
            "article_text": LONG * 10,
        })
        assert "real paragraph of body text" in body
        assert "short feed teaser" not in body

    def test_falls_back_to_the_feed_summary(self):
        from src.news_summarizer import _prepare_inputs
        _, _, body = _prepare_inputs({
            "title": "T", "source": "S", "summary": "short feed teaser",
        })
        assert "short feed teaser" in body

    def test_article_budget_is_larger_than_the_feed_budget(self):
        """A 273-char budget was the whole problem; the article needs room."""
        from src.news_summarizer import ARTICLE_CHAR_BUDGET, SUMMARY_CHAR_BUDGET
        assert ARTICLE_CHAR_BUDGET > SUMMARY_CHAR_BUDGET
