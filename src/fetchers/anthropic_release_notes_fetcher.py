"""Fetch Anthropic's platform release notes.

Anthropic was top pick 0 times in 21 digests before this source existed, and
not because the ranker was wrong. The two Anthropic listings this project
already reads — /news and /engineering — carry policy posts, safety reports
and partnership announcements, which the ranking prompt deprioritises on
purpose. The Anthropic news an applied engineer acts on is published
somewhere else entirely: the platform release notes, which this digest was
not reading. The 21-Oct-2026 entry announced API version 2026-10-21, major
versions of every client SDK, breaking changes independent of the API
version, and a licence change from MIT to Apache 2.0. None of it appeared.

This is the Anthropic twin of src/fetchers/openai_changelog_fetcher.py, and
for the same reason: there is no feed, and one server-rendered page holds the
history. The differences from OpenAI's changelog are worth knowing:

  * The unit is a date, not an entry. Each `<h3>` is a date and holds a `<ul>`
    whose every `<li>` is one change, so one item per `<li>` is one item per
    change — the same granularity the OpenAI fetcher gets from its day badges.
  * Every date heading carries an `id`, so unlike the OpenAI changelog this
    page does have a permalink per date. It is the fallback link for a change
    whose own text links nowhere.
  * The URL is platform.claude.com/docs/en/release-notes/overview. The shorter
    docs.claude.com/en/release-notes/api redirects to it, and the page's
    root-relative links — /docs/en/..., /settings/... alike — belong to the
    host it lands on, so links are resolved against the URL the fetch reached.

Headings are matched on being a date, and bodies on being list items under
one, rather than on class names: the page is built from a component library
whose class names carry a per-build hash. A shape change yields zero entries
and a warning rather than an exception, as elsewhere here — a redesign should
cost Anthropic coverage for a day, not the digest.
"""

from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import re

import requests

from src.constants import (
    ANTHROPIC_RELEASE_NOTES_MAX_ITEMS,
    ANTHROPIC_RELEASE_NOTES_SOURCE,
    ANTHROPIC_RELEASE_NOTES_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

# Anything that ends the dated section it follows. A heading that is not a
# date — "Was this page helpful?" — closes the section rather than inheriting
# it, so stray list items are not filed under yesterday's release.
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# Tags that close themselves, so they must not count toward nesting depth.
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# "October 23, 2026" and "June 20th, 2024" — both shapes are on the page, the
# ordinal suffix on the older entries.
_DATE_HEADING = re.compile(
    r"^([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})$"
)

# The page's buttons and callouts draw their icons with an icon font, which
# puts private-use codepoints in the text — a date heading arrives as
# "October 23, 2026\ue09a" and matched no date at all until these were
# dropped. Also the zero-width characters, which are invisible and would
# otherwise sit inside a word.
_DECORATION = re.compile(
    "[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd\u200b-\u200f\ufeff]"
)


def _visible(text: str) -> str:
    """Collapse whitespace and drop the icon font's private-use glyphs."""
    return " ".join(_DECORATION.sub("", text or "").split())


# How much of a change becomes its title, and how much its feed-style summary.
TITLE_CHARS = 120
SUMMARY_CHARS = 500


def _slug(text: str) -> str:
    """Reduce text to a short stable key fragment."""
    return "-".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())[:60]


def _first_sentence(body: str) -> str:
    """The release notes give changes no titles, so the opening sentence is it.

    Truncated on a word boundary rather than mid-word, because this string is
    what the reader sees in the headline list.
    """
    first = re.split(r"(?<=[.!?])\s", (body or "").strip(), maxsplit=1)[0].strip()
    if not first:
        return ""
    if len(first) <= TITLE_CHARS:
        return first
    return first[:TITLE_CHARS].rsplit(" ", 1)[0] + "…"


def _usable_href(href: str) -> str:
    """The href if it can serve as a source link, else "".

    Drops in-page anchors and anything that is not http(s) — a mailto or a
    javascript: href is not a source the reader can open.
    """
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return ""
    scheme = urlparse(href).scheme
    if scheme and scheme not in ("http", "https"):
        return ""
    return href


def _parse_date(text: str) -> datetime | None:
    """A date heading as an aware UTC datetime, or None if it is not a date."""
    match = _DATE_HEADING.match(_visible(text))
    if not match:
        return None
    month = _MONTHS.get(match.group(1).lower())
    if month is None:
        return None
    try:
        return datetime(int(match.group(3)), month, int(match.group(2)), tzinfo=timezone.utc)
    except ValueError:
        return None


class _ReleaseNotesParser(HTMLParser):
    """Walk the release notes page, emitting one record per change.

    The page is a flat sequence: a date heading, the list of changes published
    on that date, the next date heading. So a single linear pass works — the
    heading sets the date every later list item belongs to, and a list item
    closing commits a change.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries: list[dict] = []

        # The dated section being read.
        self._date: datetime | None = None
        self._anchor = ""

        # Capture state: which element we are inside, and how deep.
        self._mode: str | None = None
        self._depth = 0
        self._buf: list[str] = []
        self._heading_anchor = ""
        self._link = ""

    def _start_capture(self, mode: str):
        self._mode = mode
        self._depth = 1
        self._buf = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if self._mode is not None:
            if tag not in _VOID_TAGS:
                self._depth += 1
            if self._mode == "item" and tag == "a" and not self._link:
                self._link = _usable_href(attributes.get("href", ""))
            return

        if tag in _HEADING_TAGS:
            self._heading_anchor = attributes.get("id", "") or ""
            self._start_capture("heading")
        elif tag == "li" and self._date is not None:
            # Only inside a dated section. The page's navigation is a list too,
            # and it sits above the first date heading.
            self._link = ""
            self._start_capture("item")

    def handle_endtag(self, tag):
        if self._mode is None or tag in _VOID_TAGS:
            return
        self._depth -= 1
        if self._depth > 0:
            return
        mode, text = self._mode, "".join(self._buf)
        self._mode, self._buf = None, []
        self._commit(mode, text)

    def handle_data(self, data):
        if self._mode is not None:
            self._buf.append(data)

    def _commit(self, mode: str, raw: str):
        text = _visible(raw)

        if mode == "heading":
            # A date heading opens a section; any other heading closes the one
            # it follows.
            self._date = _parse_date(text)
            self._anchor = self._heading_anchor if self._date else ""
            return

        # mode == "item": one change, under the date above it.
        if not text or self._date is None:
            return

        title = _first_sentence(text)
        if not title:
            return

        self.entries.append({
            "title": title,
            "body": text,
            "published": self._date,
            "anchor": self._anchor,
            "link": self._link,
        })


@retry_with_backoff(exceptions=(requests.RequestException,))
def _get_release_notes() -> tuple[str, str]:
    """Fetch the release notes page. Raises so the retry decorator can see it.

    Returns the markup and the URL it was served from, which the page's
    root-relative links belong to.
    """
    response = requests.get(
        ANTHROPIC_RELEASE_NOTES_URL,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    response.raise_for_status()
    return response.text, (response.url or ANTHROPIC_RELEASE_NOTES_URL)


def parse_release_notes(
    markup: str, base_url: str = ANTHROPIC_RELEASE_NOTES_URL
) -> list[dict]:
    """Turn the release notes page into digest items, newest first.

    Returns [] on anything unexpected. The caller treats a silent source as a
    quiet day, which is the right outcome for a page that was redesigned.

    base_url is the URL the markup was served from, which is what the page's
    root-relative links resolve against.
    """
    parser = _ReleaseNotesParser()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        logger.warning("Anthropic release notes markup did not parse cleanly")

    items = []
    for entry in parser.entries:
        date = entry["published"]
        # The change's own link when its text carries one, else the permalink
        # for the date it shipped on, which every heading provides.
        if entry["link"]:
            url = urljoin(base_url, entry["link"])
        elif entry["anchor"]:
            url = f"{ANTHROPIC_RELEASE_NOTES_URL}#{entry['anchor']}"
        else:
            url = ANTHROPIC_RELEASE_NOTES_URL

        items.append({
            "title": entry["title"],
            "summary": entry["body"][:SUMMARY_CHARS],
            # Already the whole change: there is no page of its own to open,
            # and opening this one would return every release note on it.
            "article_text": entry["body"],
            "url": url,
            "source": ANTHROPIC_RELEASE_NOTES_SOURCE,
            "published": date.isoformat(),
            "type": "changelog",
            # Many changes to a page, and a link that may be shared by two of
            # them, so identity cannot come from the URL. Date plus opening
            # sentence is stable across runs, which is what the already-sent
            # filter needs.
            "identity": f"anthropic-release-notes:{date.date().isoformat()}:{_slug(entry['title'])}",
        })

    # Document order is newest first already; sorting makes that a guarantee
    # rather than an observation, and keeps the date order when a section is
    # out of place.
    items.sort(key=lambda item: item["published"], reverse=True)
    return items


def fetch_anthropic_release_notes(
    max_results: int = ANTHROPIC_RELEASE_NOTES_MAX_ITEMS,
) -> list[dict]:
    """Return recent Anthropic platform release notes, newest first."""
    try:
        markup, base_url = _get_release_notes()
    except Exception:
        logger.warning("Could not fetch the Anthropic release notes")
        return []

    items = parse_release_notes(markup, base_url)
    if not items:
        # Worth a warning rather than a shrug: the page is scraped, so zero
        # entries means a redesign far more often than it means a quiet month.
        logger.warning(
            "Parsed 0 entries from the Anthropic release notes — page shape may have changed"
        )
    else:
        logger.info("Parsed %d Anthropic release notes", len(items))
    return items[:max_results]
