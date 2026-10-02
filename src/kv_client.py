"""Minimal Vercel KV (Redis) client using urllib and REST API."""

import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


def _get_config():
    """Return KV REST API URL and token from environment."""
    url = os.getenv("KV_REST_API_URL", "").strip()
    token = os.getenv("KV_REST_API_TOKEN", "").strip()
    if not url or not token:
        raise RuntimeError("KV_REST_API_URL and KV_REST_API_TOKEN must be set")

    # Validate URL scheme to prevent SSRF
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"KV_REST_API_URL must use https (got {parsed.scheme})")
    if not parsed.hostname:
        raise ValueError("KV_REST_API_URL has no hostname")

    return url, token


def kv_configured() -> bool:
    """Whether KV credentials are present.

    Callers that treat an unconfigured KV as normal — local runs and previews,
    where topic config simply falls back to defaults — check this first so a
    missing credential stays silent instead of logging a warning per key.
    """
    return bool(
        os.getenv("KV_REST_API_URL", "").strip()
        and os.getenv("KV_REST_API_TOKEN", "").strip()
    )


def _kv_request(method, path, body=None):
    """Send a request to the Vercel KV REST API."""
    base_url, token = _get_config()
    # Validate path to prevent injection
    if path and (".." in path or path.count("//") > 1):
        raise ValueError("Invalid KV path")
    url = f"{base_url}{path}"

    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_set(key, value):
    """Set a JSON-serializable value in KV (Redis SET)."""
    payload = json.dumps(value)
    result = _kv_request("POST", "/", ["SET", key, payload])
    logger.info("KV SET %s", key)
    return result.get("result")


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_get(key):
    """Get a single value from KV (Redis GET), parsed from JSON.

    Returns None when the key is absent. Values are written by kv_set and by
    the dashboard, both of which store JSON, so a stored string round-trips;
    anything that will not parse is returned as the raw string rather than
    discarded.
    """
    result = _kv_request("POST", "/", ["GET", key])
    raw = result.get("result")
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return raw


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_append(key, value):
    """Append a JSON-serializable value to a KV list (Redis RPUSH)."""
    payload = json.dumps(value)
    result = _kv_request("POST", "/", ["RPUSH", key, payload])
    logger.info("KV RPUSH %s → list length %s", key, result.get("result"))
    return result.get("result")


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_get_list(key):
    """Get all items from a KV list (Redis LRANGE 0 -1). Returns list of parsed JSON objects."""
    result = _kv_request("POST", "/", ["LRANGE", key, "0", "-1"])
    raw_items = result.get("result", [])
    items = []
    for raw in raw_items:
        try:
            items.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            logger.warning("KV: skipping unparseable item in %s", key)
    logger.info("KV LRANGE %s → %d items", key, len(items))
    return items


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_delete(key):
    """Delete a key from KV (Redis DEL)."""
    result = _kv_request("POST", "/", ["DEL", key])
    logger.info("KV DEL %s → %s", key, result.get("result"))
    return result.get("result")


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_trim_to_last(key, count):
    """Keep only the last `count` items of a KV list (Redis LTRIM -count -1).

    The list this is used for, `digest:weekly`, is appended to once per digest
    and read whole by the dashboard's History page. The Sunday roundup used to
    clear it every week; with the roundup gone nothing else bounds it, so the
    append side caps it instead.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    result = _kv_request("POST", "/", ["LTRIM", key, str(-count), "-1"])
    logger.info("KV LTRIM %s to last %d → %s", key, count, result.get("result"))
    return result.get("result")
