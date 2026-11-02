"""Tests for the SSRF guard.

Item URLs come from feeds, scraped listing pages, Hacker News and HF Papers,
and the pipeline opens every one of them from inside a job that holds the
Telegram, OpenAI and KV secrets. These tests pin the shapes that must never
reach a socket, and the one that must still get through — a plain public
article link, because the digest is nothing without those.

DNS is patched throughout: the suite must not depend on a resolver, and the
point under test is the verdict, not the lookup.
"""

import socket
from unittest.mock import patch

import pytest

from src.url_guard import (
    MAX_REDIRECTS,
    UnsafeUrlError,
    assert_fetchable,
    check_url_shape,
    is_fetchable,
)

PUBLIC_V4 = "93.184.216.34"
PUBLIC_V6 = "2606:2800:220:1:248:1893:25c8:1946"


def _resolves_to(*addresses):
    """A getaddrinfo stand-in returning the given addresses for any host."""

    def fake(host, port, *args, **kwargs):
        infos = []
        for address in addresses:
            family = socket.AF_INET6 if ":" in address else socket.AF_INET
            infos.append((family, socket.SOCK_STREAM, 6, "", (address, port or 0)))
        return infos

    return fake


class TestShape:
    """What can be judged without a resolver, and so is judged first."""

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "gopher://example.com/",
            "data:text/html,<p>x</p>",
            "ftp://example.com/x",
            "//example.com/x",
            "example.com/x",
        ],
    )
    def test_only_http_and_https_are_allowed(self, url):
        with pytest.raises(UnsafeUrlError):
            check_url_shape(url)

    @pytest.mark.parametrize("url", ["", None, "   ", "http://", "https:///path"])
    def test_a_url_without_a_host_is_refused(self, url):
        with pytest.raises(UnsafeUrlError):
            check_url_shape(url)

    def test_credentials_in_the_authority_are_refused(self):
        with pytest.raises(UnsafeUrlError, match="credentials"):
            check_url_shape("http://user:password@example.com/post")

    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/admin",
            "http://127.1/admin",
            "http://2130706433/",
            "http://0177.0.0.1/",
            "https://169.254.169.254/latest/meta-data/",
            "http://10.0.0.5/",
            "http://192.168.1.1/",
            "http://172.16.4.4/",
            "http://[::1]/",
            "http://[fd00::1]/",
            "http://[::ffff:127.0.0.1]/",
            "http://0.0.0.0/",
            "http://100.64.0.1/",
        ],
    )
    def test_private_and_loopback_literals_are_refused_without_dns(self, url):
        """No lookup needed, and none made: the address is right there.

        Including the spellings that are not dotted quads — 127.1,
        2130706433, 0177.0.0.1 all reach 127.0.0.1 through the C resolver.
        """
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("no DNS")):
            with pytest.raises(UnsafeUrlError):
                check_url_shape(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost:8000/",
            "http://LOCALHOST/",
            "http://api.localhost/",
            "http://printer.local/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://vault.internal/secret",
            "http://host.home.arpa/",
            "http://metadata/",
        ],
    )
    def test_internal_only_names_are_refused(self, url):
        with pytest.raises(UnsafeUrlError):
            check_url_shape(url)

    def test_a_trailing_dot_does_not_slip_localhost_through(self):
        with pytest.raises(UnsafeUrlError):
            check_url_shape("http://localhost./")

    def test_a_public_article_url_passes(self):
        assert check_url_shape("https://openai.com/index/some-post") == "openai.com"

    def test_a_public_url_with_a_port_passes(self):
        assert check_url_shape("https://blog.example.com:8443/post") == "blog.example.com"


class TestResolution:
    def test_a_public_name_is_fetchable(self):
        with patch.object(socket, "getaddrinfo", _resolves_to(PUBLIC_V4, PUBLIC_V6)):
            assert assert_fetchable("https://openai.com/index/x") == "openai.com"

    def test_a_name_resolving_to_loopback_is_refused(self):
        """A plain public-looking name whose DNS answer points back at the job."""
        with patch.object(socket, "getaddrinfo", _resolves_to("127.0.0.1")):
            with pytest.raises(UnsafeUrlError, match="non-public"):
                assert_fetchable("http://inside.example/")

    def test_a_name_resolving_to_the_metadata_address_is_refused(self):
        with patch.object(socket, "getaddrinfo", _resolves_to("169.254.169.254")):
            with pytest.raises(UnsafeUrlError, match="non-public"):
                assert_fetchable("http://metadata.evil.example/")

    def test_one_private_answer_among_public_ones_is_enough_to_refuse(self):
        """Which address requests connects to is not ours to choose."""
        with patch.object(socket, "getaddrinfo", _resolves_to(PUBLIC_V4, "10.1.2.3")):
            with pytest.raises(UnsafeUrlError, match="non-public"):
                assert_fetchable("http://split.example/")

    def test_a_name_that_does_not_resolve_is_refused_not_allowed(self):
        """"I could not tell" is not a pass; the caller skips the fetch either way."""
        with patch.object(socket, "getaddrinfo", side_effect=socket.gaierror("nope")):
            with pytest.raises(UnsafeUrlError, match="did not resolve"):
                assert_fetchable("http://gone.example/")

    def test_an_unreadable_port_is_refused(self):
        with pytest.raises(UnsafeUrlError):
            assert_fetchable("http://example.com:notaport/x")


class TestIsFetchable:
    def test_true_for_a_public_url(self):
        with patch.object(socket, "getaddrinfo", _resolves_to(PUBLIC_V4)):
            assert is_fetchable("https://openai.com/index/x") is True

    def test_false_rather_than_raising_for_a_blocked_url(self):
        assert is_fetchable("http://169.254.169.254/latest/meta-data/") is False


def test_redirect_budget_is_small_enough_to_be_a_budget():
    """A real article redirects once or twice; a long chain is a walk-around."""
    assert 1 <= MAX_REDIRECTS <= 10
