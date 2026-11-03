"""Fetch latest releases from key ML/AI GitHub repos."""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

from src.constants import GITHUB_REPOS, REQUEST_TIMEOUT, USER_AGENT
from src.logger import get_logger

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com/repos"

# Release-candidate, alpha, beta and dev markers in a version tag, in the
# spellings the tracked repos use: v0.33.0rc3, v1.2.0-rc.1, v0.9.0-alpha,
# v1.0.0.dev2, v1.0.0-pre. Matched case-insensitively and anchored to a digit
# or a separator on the left so it cannot fire inside a word. PEP 440's bare
# letter forms (v2.0.0b1) are deliberately not matched: none of the tracked
# repos tags that way, and a lone "b" collides with llama.cpp's build numbers,
# which have a rule of their own below.
PRERELEASE_TAG = re.compile(
    r"(?:[\d.\-_]|^)(?:rc|alpha|beta|dev|pre)[\d.\-_]*$", re.IGNORECASE
)


def _fetch_latest_release(repo: str, headers: dict) -> dict | None:
    """Fetch the latest release for a single repo. Returns None on failure or skip."""
    url = f"{GITHUB_API_BASE}/{repo}/releases/latest"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read())
    except Exception:
        logger.warning("Could not fetch release for %s", repo)
        return None

    # Skip pre-releases
    if data.get("prerelease"):
        return None

    # Skip releases older than 24 hours
    published_str = data.get("published_at", "")
    if not published_str:
        return None

    try:
        published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    if published_dt < cutoff:
        return None

    tag_name = data.get("tag_name", "")

    # Skip a release candidate the publisher did not flag as one.
    #
    # The `prerelease` check above cannot catch these twice over: /releases/
    # latest never returns a release GitHub considers a prerelease, and a
    # project that tags release candidates as full releases is reported with
    # `prerelease: false`. vLLM does exactly that, so on 02-Nov-2026
    # `vllm v0.33.0rc3 released` passed every filter here — `v?\d+\.\d+\.\d+`
    # does not fullmatch a tag ending `rc3`, so the patch rule missed it too —
    # and, as the only candidate the ranker kept out of five, it was the whole
    # of that day's digest. A release candidate is not the day's most
    # significant AI development.
    if PRERELEASE_TAG.search(tag_name):
        logger.info("Skipping pre-release %s %s", repo, tag_name)
        return None

    # Skip build-number releases (e.g. b8671, b8672) — these are incremental builds
    if re.fullmatch(r"b\d+", tag_name):
        return None

    # Skip patch releases. A non-zero patch component is a bugfix by semver
    # convention, so it cannot be the day's most significant AI development.
    # Majors and minors still pass — those can carry real capability changes.
    patch = re.fullmatch(r"v?\d+\.\d+\.([1-9]\d*)", tag_name)
    if patch:
        logger.info("Skipping patch release %s %s", repo, tag_name)
        return None

    body = data.get("body", "") or ""

    # Skip releases with thin descriptions (< 200 chars) — not meaningful
    if len(body.strip()) < 200:
        return None

    repo_name = repo.split("/")[-1]

    return {
        "title": f"{repo_name} {tag_name} released",
        "summary": body[:500],
        "url": data.get("html_url", ""),
        "source": "GitHub",
        "repo": repo_name,
        "version": tag_name,
        "published": published_str,
        "type": "release",
    }


def fetch_github_releases() -> list[dict]:
    """Fetch latest releases from tracked GitHub repos.

    Uses GITHUB_TOKEN env var for authentication (increases rate limit).
    """
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    releases = []
    for repo in GITHUB_REPOS:
        result = _fetch_latest_release(repo, headers)
        if result:
            releases.append(result)
            logger.info("Found release: %s", result["title"])

    releases.sort(key=lambda x: x.get("published", ""), reverse=True)
    return releases
