"""Decide whether a URL taken from third-party content is safe to fetch.

Item URLs are not this project's own: they come from feeds, from scraped
listing pages, from Hacker News and from Hugging Face Papers, and
src/article_fetcher.py opens every one of them before ranking. Nothing checked
where they pointed, so an item whose link was `http://169.254.169.254/...` or
`http://localhost:8000/admin` got that request made from inside the job — the
classic server-side request forgery shape. The pipeline runs in GitHub Actions
with the Telegram, OpenAI and KV secrets in its environment; GitHub-hosted
runners expose no useful metadata service today, which is what kept this a
medium finding rather than a high one, but the guard is what keeps that true
if the job ever moves to a self-hosted runner or a cloud VM.

What a safe URL means here:

* http or https, and nothing else — no file://, no gopher://, no data:.
* No credentials in the authority (`http://user:pass@host`), which some
  proxies and libraries hand on in ways the author did not intend.
* A hostname that is not a loopback or internal-only name.
* Every address the hostname resolves to is a global unicast address. Not
  "the first one": a name that resolves to one public and one private address
  is rejected, because which one `requests` connects to is not ours to choose.

Redirects are checked the same way, hop by hop — a public URL that answers
302 to `http://127.0.0.1/` is the usual way around a check done only on the
URL that was handed in. That loop lives in article_fetcher._get, which is what
holds the connection; this module gives it the per-hop verdict.

DNS is consulted, so the resolution the guard sees and the one the connection
makes are two separate lookups — a rebinding window this does not close.
Closing it properly means connecting to a pinned address, which with requests
means a custom transport adapter and breaks TLS hostname verification. For a
job whose only unprotected neighbours are on the runner itself, a resolve-then-
check guard with a redirect walk is the proportionate control.
"""

import ipaddress
import socket
from urllib.parse import urlsplit

from src.logger import get_logger

logger = get_logger(__name__)

ALLOWED_SCHEMES = ("http", "https")

# Hostnames that never name something on the public internet, whatever DNS
# says about them. `.internal` is the cloud convention (including GCP's
# metadata server), `.local` is mDNS, and a resolver that happens to answer
# for any of these should not get the benefit of the doubt.
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".home.arpa",
)
_BLOCKED_HOSTS = ("localhost", "metadata", "metadata.google.internal")

# How many hops a fetch may follow. Real articles redirect once or twice
# (http to https, a tracking URL to the post); a longer chain is either a loop
# or someone walking the guard.
MAX_REDIRECTS = 4


class UnsafeUrlError(ValueError):
    """Raised when a URL must not be fetched. Carries why, for the log."""


def _address_is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Whether an address is global unicast and so worth connecting to.

    `is_global` already excludes loopback, RFC-1918, link-local (and with it
    169.254.169.254), carrier-grade NAT, documentation ranges and IPv6
    unique-local. The explicit flags after it are belt and braces, and make
    the intent readable to the next person.
    """
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped

    if any(
        (
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    ):
        return False
    return bool(ip.is_global)


def _as_literal_address(host: str):
    """The address `host` spells literally, or None if it is a name.

    Not just `ip_address`: 127.0.0.1 also spells as `127.1`, `2130706433` and
    `0177.0.0.1`, and every one of those is accepted by the C resolver and by
    curl. `inet_aton` reads all of them and consults no DNS, so these forms
    are rejected here rather than one lookup later.
    """
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    try:
        packed = socket.inet_aton(host)
    except OSError:
        return None
    return ipaddress.IPv4Address(packed)


def check_url_shape(url: str) -> str:
    """Validate what can be judged without a lookup. Returns the hostname.

    Separate from the DNS check so the cheap, deterministic rejections happen
    at the top of the pipeline and the tests that exercise fetching stay
    hermetic — only the code that actually opens a socket resolves a name.
    """
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("empty URL")

    try:
        parts = urlsplit(url.strip())
    except ValueError as exc:
        raise UnsafeUrlError(f"unparseable URL: {exc}") from exc

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme {parts.scheme or 'missing'!r} is not http or https")

    if parts.username or parts.password:
        raise UnsafeUrlError("URL carries credentials in its authority")

    try:
        host = parts.hostname
    except ValueError as exc:
        raise UnsafeUrlError(f"unreadable host: {exc}") from exc
    if not host:
        raise UnsafeUrlError("URL has no host")

    host = host.rstrip(".").lower()
    if not host:
        raise UnsafeUrlError("URL has no host")

    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError(f"host {host!r} is not a public name")

    # A literal address needs no resolver, and is the most direct way this
    # would be attempted.
    literal = _as_literal_address(host)
    if literal is not None and not _address_is_public(literal):
        raise UnsafeUrlError(f"address {literal} is not a public address")

    return host


def resolved_addresses(host: str, port: int | None = None) -> list[str]:
    """Every address `host` resolves to, or raise UnsafeUrlError.

    A resolution failure is reported as unsafe rather than as a network error:
    the caller's only move either way is to skip the fetch, and treating "I
    could not tell" as safe is how a guard stops guarding.
    """
    try:
        infos = socket.getaddrinfo(host, port or 0, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError) as exc:
        raise UnsafeUrlError(f"host {host!r} did not resolve: {exc}") from exc

    addresses = []
    for info in infos:
        address = info[4][0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise UnsafeUrlError(f"host {host!r} resolved to nothing")
    return addresses


def assert_fetchable(url: str) -> str:
    """Raise UnsafeUrlError unless this URL may be fetched. Returns the host.

    Call it for the URL handed in *and* for every redirect target, before the
    request that follows it.
    """
    host = check_url_shape(url)
    parts = urlsplit(url.strip())
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrlError(f"bad port: {exc}") from exc

    for address in resolved_addresses(host, port):
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise UnsafeUrlError(f"host {host!r} resolved to {address!r}: {exc}") from exc
        if not _address_is_public(ip):
            raise UnsafeUrlError(f"host {host!r} resolves to the non-public address {address}")

    return host


def is_fetchable(url: str) -> bool:
    """assert_fetchable as a boolean, with the reason logged."""
    try:
        assert_fetchable(url)
    except UnsafeUrlError as exc:
        logger.info("Refusing to fetch %s: %s", url, exc)
        return False
    return True
