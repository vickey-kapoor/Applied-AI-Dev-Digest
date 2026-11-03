"""Which GitHub releases count as a shipped AI development.

The version-string rules are the whole of this fetcher's editorial judgement,
and one of them was missing: on 02-Nov-2026 `vllm v0.33.0rc3 released` reached
the ranker, was the only candidate it kept out of five, and was that day's
entire digest.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.fetchers.github_fetcher import PRERELEASE_TAG, _fetch_latest_release


def _release(tag: str, **over) -> dict:
    """A GitHub /releases/latest payload that passes every other filter."""
    payload = {
        "tag_name": tag,
        "prerelease": False,
        "published_at": (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z"),
        "body": "A release note long enough to clear the 200-character floor. " * 5,
        "html_url": f"https://github.com/vllm-project/vllm/releases/tag/{tag}",
    }
    payload.update(over)
    return payload


@pytest.fixture
def api(monkeypatch):
    """Serve one payload in place of the GitHub API."""
    def serve(payload):
        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                import json

                return json.dumps(payload).encode()

        monkeypatch.setattr(
            "src.fetchers.github_fetcher.urllib.request.urlopen",
            lambda *a, **k: _Resp(),
        )
    return serve


class TestPrereleaseTag:
    """The spellings a tracked repo uses for a candidate build."""

    @pytest.mark.parametrize(
        "tag",
        ["v0.33.0rc3", "v0.11.0rc2", "v1.2.0-rc.1", "v0.9.0-alpha", "v1.0.0.dev2",
         "v1.0.0-pre", "V2.0.0RC1"],
    )
    def test_matches_a_candidate_build(self, tag):
        assert PRERELEASE_TAG.search(tag)

    @pytest.mark.parametrize(
        "tag",
        ["v0.33.0", "v1.2.0", "v4.57.0", "transformers-v5.0.0", "b8671", "v2.0.0"],
    )
    def test_leaves_a_real_release_alone(self, tag):
        assert not PRERELEASE_TAG.search(tag)

    def test_does_not_fire_inside_a_word(self):
        """"pre" and "dev" are common in project names, not just in versions."""
        assert not PRERELEASE_TAG.search("predictor-v1.0.0")
        assert not PRERELEASE_TAG.search("devtools-v2.1.0")


class TestFetchLatestRelease:
    def test_skips_a_release_candidate_the_publisher_did_not_flag(self, api):
        """vLLM tags candidates as full releases, so `prerelease` is false.

        This is the 02-Nov-2026 digest. The `prerelease` flag said no, and the
        patch rule (`v?\\d+\\.\\d+\\.\\d+`) does not fullmatch a tag ending
        `rc3`, so nothing stopped it.
        """
        api(_release("v0.33.0rc3"))
        assert _fetch_latest_release("vllm-project/vllm", {}) is None

    def test_keeps_the_real_release_of_the_same_minor(self, api):
        api(_release("v0.33.0"))
        result = _fetch_latest_release("vllm-project/vllm", {})
        assert result is not None
        assert result["title"] == "vllm v0.33.0 released"

    def test_still_skips_a_flagged_prerelease(self, api):
        api(_release("v0.34.0", prerelease=True))
        assert _fetch_latest_release("vllm-project/vllm", {}) is None
