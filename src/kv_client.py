"""Minimal Vercel KV (Redis) client using urllib and REST API."""

import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError

from src.logger import get_logger
from src.utils.retry import retry_with_backoff

logger = get_logger(__name__)


def _get_config():
    """Return KV REST API URL and token from environment."""
    url = os.getenv("KV_REST_API_URL")
    token = os.getenv("KV_REST_API_TOKEN")
    if not url or not token:
        raise RuntimeError("KV_REST_API_URL and KV_REST_API_TOKEN must be set")
    return url, token


def _kv_request(method, path, body=None):
    """Send a request to the Vercel KV REST API."""
    base_url, token = _get_config()
    url = f"{base_url}{path}"

    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(URLError, OSError))
def kv_set(key, value):
    """Set a JSON-serializable value in KV (Redis SET)."""
    payload = json.dumps(value)
    result = _kv_request("POST", "/", ["SET", key, payload])
    logger.info("KV SET %s", key)
    return result.get("result")


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(URLError, OSError))
def kv_append(key, value):
    """Append a JSON-serializable value to a KV list (Redis RPUSH)."""
    payload = json.dumps(value)
    result = _kv_request("POST", "/", ["RPUSH", key, payload])
    logger.info("KV RPUSH %s → list length %s", key, result.get("result"))
    return result.get("result")


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(URLError, OSError))
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


@retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(URLError, OSError))
def kv_delete(key):
    """Delete a key from KV (Redis DEL)."""
    result = _kv_request("POST", "/", ["DEL", key])
    logger.info("KV DEL %s → %s", key, result.get("result"))
    return result.get("result")
