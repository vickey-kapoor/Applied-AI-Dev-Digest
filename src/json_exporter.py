"""The digest's own record of what it has sent.

`digests.json` is one entry per day, and `get_sent_top_paper_ids` reads it back
so a story cannot be the top pick twice. It is the only JSON the pipeline keeps:
`papers.json`, a 500-item rolling archive, was written for the Vercel dashboard
and read by nothing else.
"""

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from src.constants import DIGEST_CAP_DAYS
from src.logger import get_logger

logger = get_logger(__name__)

# Data directory path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Allowed filenames for JSON data files
_SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-]+\.json$")


def _validate_filename(filename: str) -> str:
    """Validate and resolve a safe filepath within DATA_DIR."""
    if not _SAFE_FILENAME.match(filename):
        raise ValueError(f"Invalid filename: {filename}")
    filepath = os.path.join(DATA_DIR, filename)
    # Prevent path traversal
    if not os.path.abspath(filepath).startswith(os.path.abspath(DATA_DIR)):
        raise ValueError(f"Path traversal detected: {filename}")
    return filepath


def ensure_data_dir():
    """Ensure the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filename: str) -> dict:
    """Load JSON file from data directory."""
    filepath = _validate_filename(filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in %s, returning empty dict", filename)
        return {}


def save_json(filename: str, data: dict):
    """Save JSON file to data directory."""
    ensure_data_dir()
    filepath = _validate_filename(filename)
    fd, temp_path = tempfile.mkstemp(
        prefix=f".{filename}.",
        suffix=".tmp",
        dir=DATA_DIR,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
    logger.info("Saved %s", filepath)


def _identity_title(title: str) -> str:
    """Normalize a title for identity keys: case and whitespace only.

    Deliberately conservative. Punctuation is significant here — it is part of
    what separates one release from another — so this must not be swapped for
    fetcher._fuzzy_title, which strips it.
    """
    return " ".join((title or "").strip().lower().split())


def _paper_identity(item: dict) -> str:
    """Build a stable identity key for a paper.

    An explicit identity wins, for sources where one URL covers many items.
    OpenAI's changelog is a single page with no per-entry permalinks, so keying
    on the URL would give all 174 entries the same id — and once one had been
    sent, get_sent_top_paper_ids would suppress the source for good.
    src.fetcher._identity_of reads the same field, so deduplication and
    already-sent both agree on what one item is.
    """
    identity = (item.get("identity") or "").strip().lower()
    if identity:
        return f"id:{identity}"

    url = (item.get("url") or "").strip().lower()
    if url:
        return f"url:{url}"

    source = (item.get("source") or "unknown").strip().lower()
    title = _identity_title(item.get("title", ""))
    return f"title:{source}:{title}"


def _paper_id_for_item(item: dict) -> str:
    """Generate a deterministic ID for new papers."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, _paper_identity(item)))


def get_sent_top_paper_ids() -> set[str]:
    """Return all top_paper_ids that have been sent in past digests."""
    data = load_json("digests.json")
    return {
        d["top_paper_id"]
        for d in data.get("digests", [])
        if d.get("top_paper_id") and d.get("telegram_sent", False)
    }


def export_digest(
    top_paper_id: str,
    papers_fetched: int,
    telegram_sent: bool = False,
    workflow_run_id: str = None
):
    """
    Export digest entry to digests.json.

    Args:
        top_paper_id: ID of the top-ranked paper
        papers_fetched: Number of papers fetched
        telegram_sent: Whether Telegram message was sent
        workflow_run_id: GitHub Actions run ID (optional)

    The entry records run_at (full UTC timestamp) alongside the date. GitHub's
    scheduler has delivered this workflow up to 9 hours late, which pushes a
    run past midnight onto the next date; run_at makes that visible rather than
    leaving an unexplained gap in the record.
    """
    data = load_json("digests.json")
    if "digests" not in data:
        data["digests"] = []

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    run_at = now.isoformat().replace("+00:00", "Z")

    # Check if digest for today already exists
    for digest in data["digests"]:
        if digest.get("date") == today:
            # Update existing entry. Two runs can land on one UTC date when
            # GitHub's scheduler delivers late — record run_at so the drift is
            # visible instead of the second run silently overwriting the first.
            previous_run_at = digest.get("run_at")
            digest["top_paper_id"] = top_paper_id
            digest["papers_fetched"] = papers_fetched
            digest["telegram_sent"] = telegram_sent
            digest["run_at"] = run_at
            if previous_run_at:
                digest["previous_run_at"] = previous_run_at
                logger.warning(
                    "Second run for %s (previous at %s) — scheduler drift crossed a date boundary",
                    today,
                    previous_run_at,
                )
            if workflow_run_id:
                digest["workflow_run_id"] = workflow_run_id
            save_json("digests.json", data)
            logger.info("Updated digest for %s", today)
            return

    # Create new entry
    digest = {
        "date": today,
        "run_at": run_at,
        "top_paper_id": top_paper_id or "",
        "papers_fetched": papers_fetched,
        "telegram_sent": telegram_sent,
        "workflow_run_id": workflow_run_id or ""
    }

    # Add to beginning of list
    data["digests"].insert(0, digest)

    # Keep only last N days
    data["digests"] = data["digests"][:DIGEST_CAP_DAYS]

    save_json("digests.json", data)
    logger.info("Exported digest for %s", today)
