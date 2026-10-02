"""Fetch and extract the readable text of a linked article.

The summarizer used to see only what the feed gave it: a median of 273
characters of RSS teaser, never the post itself. Five structured fields were
being written from roughly two sentences, and `availability` — the field that
usually decides whether the reader can act on an item — came back "not stated"
39% of the time. Raising the truncation limit would not have helped; no item
even reached it, because the feeds themselves are that thin.

This module opens the link instead. Extraction is deliberately dependency-free
and heuristic rather than a readability port: prefer <article> or <main> when
the page marks one, drop the furniture (nav, scripts, footers), and keep the
block-level text. Good enough beats exact here — the consumer is a model that
tolerates some noise, and the cost of a wrong guess is a slightly worse brief,
not a crash.

Every failure path returns "" so the caller falls back to the RSS summary. A
paywall, a JS-rendered page or a bot block must never take the digest down.
"""

from html.parser import HTMLParser
import html as html_module

import requests

from src.constants import REQUEST_TIMEOUT, USER_AGENT
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

# Enough for a long launch post; well past what any brief needs, and a bound on
# what a hostile or generated page can push into the prompt.
MAX_ARTICLE_CHARS = 12000

# Stop reading a response this large: a page bigger than this is not an article.
MAX_DOWNLOAD_BYTES = 2_000_000

# Below this, extraction effectively failed — a cookie wall or a JS shell — and
# the RSS summary is the better input.
MIN_USEFUL_CHARS = 400

_SKIP_TAGS = {
    "script", "style", "noscript", "svg", "nav", "header", "footer",
    "aside", "form", "button", "select", "iframe", "template",
}

_BLOCK_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "li", "blockquote", "pre",
    "td", "th", "figcaption", "dd", "dt",
}

# Containers that usually wrap the real body. When one is present its contents
# are preferred over the whole page, which is what removes most boilerplate.
_MAIN_TAGS = {"article", "main"}


class _ArticleExtractor(HTMLParser):
    """Collect block-level text, tracking whether we are inside <article>/<main>.

    Both collections are built in one pass so the caller can prefer the scoped
    text and fall back to the whole page when the site marks up neither.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._main_depth = 0
        self._block: list[str] = []
        self._in_block = False
        self.all_blocks: list[str] = []
        self.main_blocks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _MAIN_TAGS:
            self._main_depth += 1
        elif tag in _BLOCK_TAGS:
            self._flush()
            self._in_block = True

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _MAIN_TAGS:
            self._main_depth = max(0, self._main_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._skip_depth or not self._in_block:
            return
        text = data.strip()
        if text:
            self._block.append(text)

    def _flush(self):
        if self._block:
            line = " ".join(self._block).strip()
            # One-word fragments are nearly always labels or icon text.
            if len(line.split()) > 1:
                self.all_blocks.append(line)
                if self._main_depth:
                    self.main_blocks.append(line)
            self._block = []
        self._in_block = False

    def close(self):
        self._flush()
        super().close()


def extract_text(markup: str) -> str:
    """Pull the readable body out of HTML. Returns "" if nothing usable is left."""
    parser = _ArticleExtractor()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        # A malformed page is common and not worth a traceback; whatever the
        # parser accumulated before giving up is still usable.
        logger.debug("Article markup did not parse cleanly")

    blocks = parser.main_blocks if len(" ".join(parser.main_blocks)) >= MIN_USEFUL_CHARS else parser.all_blocks
    text = html_module.unescape("\n".join(blocks)).strip()
    return text[:MAX_ARTICLE_CHARS]


@retry_with_backoff(exceptions=(requests.RequestException,))
def _get(url: str) -> requests.Response:
    return requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        stream=True,
    )


def fetch_article_text(url: str) -> str:
    """Return the article's readable text, or "" if it cannot be had.

    Never raises: the caller's fallback is the RSS summary, and a digest that
    skips a day because a blog was down would be worse than a thin brief.
    """
    if not url or not url.startswith(("http://", "https://")):
        return ""

    try:
        response = _get(url)
        with response:
            if response.status_code != 200:
                logger.info("Article fetch got HTTP %s for %s", response.status_code, url)
                return ""

            content_type = response.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                logger.info("Article is not HTML (%s): %s", content_type or "no type", url)
                return ""

            # Read with a cap rather than trusting Content-Length, which is
            # absent on chunked responses.
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=65536, decode_unicode=True):
                if not chunk:
                    continue
                if isinstance(chunk, bytes):
                    chunk = chunk.decode(response.encoding or "utf-8", errors="replace")
                chunks.append(chunk)
                total += len(chunk)
                if total >= MAX_DOWNLOAD_BYTES:
                    break
            markup = "".join(chunks)
    except Exception:
        logger.info("Could not fetch article %s", url)
        return ""

    text = extract_text(markup)
    if len(text) < MIN_USEFUL_CHARS:
        logger.info("Article extraction too thin (%d chars), using the feed summary: %s", len(text), url)
        return ""

    logger.info("Read %d chars from %s", len(text), url)
    return text
