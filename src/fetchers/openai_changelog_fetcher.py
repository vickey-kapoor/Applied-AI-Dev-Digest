"""Fetch OpenAI's developer changelog.

Every post on OpenAI's news blog — openai.com/index/* — is behind Cloudflare
bot mitigation. The response carries `cf-mitigated: challenge` and returns 403
with an `accept-ch: Sec-CH-UA-*` client-hint demand, identically for this
project's user agent, for curl's, and for no user agent at all. It is not a
user-agent filter and no header makes it go away; only a browser engine would,
which is the thing we are not going to do. Their RSS feed is readable but
carries only each page's meta description: 1,243 entries, every one a single
sentence of roughly 150 characters, with no content:encoded. Measured against a
live candidate pool, OpenAI items reached the summarizer with 148 and 152
characters while every other source gave between 2,780 and 12,000.

platform.openai.com/docs/changelog is not challenged, and for this reader it is
the better source regardless. The news blog's three most recent entries are
"The eternal complement", "How Albertsons Companies is reimagining retail from
the inside out" and "The Den frees up 10-15 hours a week to grow with ChatGPT
Work". The changelog's are a new model with its per-million-token prices, a
service tier that cuts the time between output tokens, and an image-encoding
bug worth re-running evaluations over. That is the OpenAI news an applied
engineer acts on.

There is no feed and no per-entry permalink, so this parses the page. Hashed
CSS class names are matched on their stable prefix — `_ChangelogMarkdown_`,
never `_ChangelogMarkdown_pvkq8_19` — and a shape change yields zero entries
and a warning rather than an exception: a redesign must cost OpenAI coverage
for a day, not the digest.
"""

from datetime import datetime, timezone
from html.parser import HTMLParser
import re

import requests

from src.constants import (
    OPENAI_CHANGELOG_MAX_ITEMS,
    OPENAI_CHANGELOG_SOURCE,
    OPENAI_CHANGELOG_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)

# Class-name fragments that survive a rebuild; the hash suffix does not.
_MONTH_HEADING_CLASS = "_ChangelogSectionTitle_"
_BODY_CLASS = "_ChangelogMarkdown_"
_BADGE_CLASS = "_Badge_"

# Tags that close themselves, so they must not count toward nesting depth.
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Inside an entry body, these end a line; everything else runs on.
_BODY_BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "tr"}

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "September, 2026" — the day badges carry no year, so the enclosing heading
# supplies it.
_MONTH_HEADING = re.compile(r"([A-Za-z]+),?\s+(\d{4})")

# "Sep 29" on the outline badge that opens each entry.
_DAY_BADGE = re.compile(r"^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})$")

# How much of an entry becomes its title, and how much its feed-style summary.
TITLE_CHARS = 120
SUMMARY_CHARS = 500


def _slug(text: str) -> str:
    """Reduce text to a short stable key fragment."""
    return "-".join(re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split())[:60]


def _first_sentence(body: str) -> str:
    """The changelog gives entries no titles, so the opening sentence is it.

    Truncated on a word boundary rather than mid-word, because this string is
    what the reader sees in the headline list.
    """
    first = re.split(r"(?<=[.!?])\s", (body or "").strip(), maxsplit=1)[0].strip()
    if not first:
        return ""
    if len(first) <= TITLE_CHARS:
        return first
    return first[:TITLE_CHARS].rsplit(" ", 1)[0] + "…"


class _ChangelogParser(HTMLParser):
    """Walk the changelog page, emitting one record per dated entry.

    The page lists entries in document order under a month heading, each as a
    day badge, then any number of badges naming the change type and the models
    or endpoints it affects, then the body. That order is what lets a single
    linear pass work: badges accumulate, and the body closing is what commits
    an entry.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries: list[dict] = []
        self._year: int | None = None

        # Pending state for the entry being read.
        self._day = ""
        self._category = ""
        self._tags: list[str] = []

        # Capture state: which element we are inside, and how deep.
        self._mode: str | None = None
        self._depth = 0
        self._buf: list[str] = []
        self._badge_variant = ""
        self._badge_is_category = False

    # -- capture plumbing -------------------------------------------------

    def _start_capture(self, mode: str):
        self._mode = mode
        self._depth = 1
        self._buf = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "") or ""

        if self._mode is not None:
            if tag not in _VOID_TAGS:
                self._depth += 1
            if self._mode == "badge" and tag == "span" and "capitalize" in classes:
                self._badge_is_category = True
            if self._mode == "body" and tag in _BODY_BLOCK_TAGS:
                self._buf.append("\n")
            return

        if _MONTH_HEADING_CLASS in classes:
            self._start_capture("heading")
        elif _BADGE_CLASS in classes:
            self._badge_variant = attributes.get("data-variant", "")
            self._badge_is_category = False
            self._start_capture("badge")
        elif _BODY_CLASS in classes:
            self._start_capture("body")

    def handle_startendtag(self, tag, attrs):
        # <br/> and friends: nothing to capture, and nothing to count.
        if self._mode == "body" and tag == "br":
            self._buf.append("\n")

    def handle_endtag(self, tag):
        if self._mode is None or tag in _VOID_TAGS:
            return
        if self._mode == "body" and tag in _BODY_BLOCK_TAGS:
            self._buf.append("\n")
        self._depth -= 1
        if self._depth > 0:
            return
        mode, text = self._mode, "".join(self._buf)
        self._mode, self._buf = None, []
        self._commit(mode, text)

    def handle_data(self, data):
        if self._mode is not None:
            self._buf.append(data)

    # -- interpretation ---------------------------------------------------

    def _commit(self, mode: str, raw: str):
        if mode == "heading":
            match = _MONTH_HEADING.search(" ".join(raw.split()))
            if match:
                self._year = int(match.group(2))
            return

        if mode == "badge":
            text = " ".join(raw.split())
            if not text:
                return
            if self._badge_variant == "outline" and _DAY_BADGE.match(text):
                # A new day badge opens a new entry: drop any badges left over
                # from a body we failed to read rather than mislabelling this one.
                self._day, self._category, self._tags = text, "", []
            elif self._badge_is_category:
                self._category = text
            else:
                self._tags.append(text)
            return

        # mode == "body": the entry is complete.
        body = "\n".join(
            " ".join(line.split()) for line in raw.split("\n") if line.strip()
        ).strip()
        published = self._published()
        title = _first_sentence(body)
        if not body or not title or published is None:
            self._day, self._category, self._tags = "", "", []
            return

        self.entries.append({
            "title": title,
            "body": body,
            "category": self._category,
            "tags": list(self._tags),
            "published": published,
        })
        self._day, self._category, self._tags = "", "", []

    def _published(self) -> datetime | None:
        match = _DAY_BADGE.match(self._day)
        if not match or self._year is None:
            return None
        month = _MONTHS.get(match.group(1).lower())
        if month is None:
            return None
        try:
            return datetime(self._year, month, int(match.group(2)), tzinfo=timezone.utc)
        except ValueError:
            return None


@retry_with_backoff(exceptions=(requests.RequestException,))
def _get_changelog() -> str:
    """Fetch the changelog page. Raises so the retry decorator can see it."""
    response = requests.get(
        OPENAI_CHANGELOG_URL,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    response.raise_for_status()
    return response.text


def parse_changelog(markup: str) -> list[dict]:
    """Turn the changelog page into digest items, newest first.

    Returns [] on anything unexpected. The caller treats a silent source as a
    quiet day, which is the right outcome for a page that was redesigned.
    """
    parser = _ChangelogParser()
    try:
        parser.feed(markup)
        parser.close()
    except Exception:
        logger.warning("OpenAI changelog markup did not parse cleanly")

    items = []
    for entry in parser.entries:
        body, tags = entry["body"], entry["tags"]
        # The affected models and endpoints are the most actionable thing on
        # the page for this reader, and they live in badges rather than prose.
        # Folding them into the body keeps the item schema unchanged and puts
        # them in front of the summarizer.
        preamble = []
        if entry["category"]:
            preamble.append(f"Change type: {entry['category']}")
        if tags:
            preamble.append(f"Affects: {', '.join(tags)}")
        article_text = "\n".join(preamble + [body]) if preamble else body

        date = entry["published"]
        items.append({
            "title": entry["title"],
            "summary": body[:SUMMARY_CHARS],
            # Already the full entry: there is no page to open, and opening
            # the changelog URL would return all 170-odd entries at once.
            "article_text": article_text,
            "url": OPENAI_CHANGELOG_URL,
            "source": OPENAI_CHANGELOG_SOURCE,
            "published": date.isoformat(),
            "type": "changelog",
            # One page, many entries, no permalinks — so the identity cannot
            # come from the URL. Date plus opening sentence is stable across
            # runs, which is what the already-sent filter needs.
            "identity": f"openai-changelog:{date.date().isoformat()}:{_slug(entry['title'])}",
        })

    items.sort(key=lambda item: item["published"], reverse=True)
    return items


def fetch_openai_changelog(max_results: int = OPENAI_CHANGELOG_MAX_ITEMS) -> list[dict]:
    """Return recent OpenAI platform changelog entries, newest first."""
    try:
        markup = _get_changelog()
    except Exception:
        logger.warning("Could not fetch the OpenAI changelog")
        return []

    items = parse_changelog(markup)
    if not items:
        # Worth a warning rather than a shrug: the page is scraped, so zero
        # entries means a redesign far more often than it means a quiet month.
        logger.warning("Parsed 0 entries from the OpenAI changelog — page shape may have changed")
    else:
        logger.info("Parsed %d OpenAI changelog entries", len(items))
    return items[:max_results]
