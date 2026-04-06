"""Fetch latest releases from key ML/AI GitHub repos."""

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone

from src.constants import GITHUB_REPOS, REQUEST_TIMEOUT
from src.logger import get_logger

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com/repos"


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

    # Skip build-number releases (e.g. b8671, b8672) — these are incremental builds
    if re.fullmatch(r"b\d+", tag_name):
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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI-Dev-Digest"}
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
