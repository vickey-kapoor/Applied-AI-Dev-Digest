"""Minimal Vercel KV (Redis) client using urllib and REST API.

Three calls, all of them for the daily send claim in src/digest_claim.py, which
is the one thing KV still holds: it is what stops two overlapping runs sending
the same digest twice. The set/get/list calls that lived here served the Vercel
dashboard's topic config, feedback log and history list, and went with it.
"""

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

    A local run with no credentials is normal: the claim is only needed where
    two runs can overlap, which is GitHub Actions. Callers check this first so
    a missing credential stays silent instead of warning per key.
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
def kv_delete(key):
    """Delete a key from KV (Redis DEL)."""
    result = _kv_request("POST", "/", ["DEL", key])
    logger.info("KV DEL %s → %s", key, result.get("result"))
    return result.get("result")


@retry_with_backoff(exceptions=(URLError, OSError))
def kv_set_if_absent(key, value, ttl_seconds=None) -> bool:
    """Set `key` only if it does not exist (Redis SET ... NX), optionally with
    a TTL. Returns True when this caller is the one that set it.

    This is the only KV call whose *return* carries the meaning rather than the
    stored value: two runners racing for the same key both succeed at the HTTP
    level and exactly one gets True. Redis replies "OK" to the winner and null
    to everyone else.
    """
    command = ["SET", key, json.dumps(value), "NX"]
    if ttl_seconds is not None:
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")
        command += ["EX", str(int(ttl_seconds))]

    result = _kv_request("POST", "/", command)
    acquired = result.get("result") is not None
    logger.info("KV SET %s NX → %s", key, "acquired" if acquired else "already set")
    return acquired
