"""One send per day, decided outside the git checkout.

src/schedule_guard.py keeps its "has today already run" state in
data/schedule_state.json, which the workflow commits after each send. That
works for ticks that arrive in sequence, and fails for two runs that overlap,
because a run reads the state from the commit it was *created* at. On
20-Oct-2026 an hourly tick honoured at 09:49 local held for noon and sent at
12:01:19; the external scheduler's dispatch was created at 12:01:02, pinned to
the previous day's commit, and queued behind the holding run by the workflow's
concurrency group. It then checked out a state file that still said 19-Oct,
read the day as unsent, and sent the digest a second time. (Its push was
rejected as non-fast-forward, which is how the duplicate showed up as a failed
run rather than a second commit.) The same race decided the other way on
07-Oct, when the send happened to commit 6 seconds before the dispatch was
created — so it has always been a coin flip, not a new bug.

The fix is a claim that does not live in the repository: a Redis SET NX on a
date-keyed KV key, which exactly one of any number of concurrent runs can win.
It is checked after the guard, so a tick with nothing due still costs nothing,
and it gates the send itself rather than only the commit.

A claim is released when the send fails, so the day can be retried; a claim
held by a run that sent and then failed to push is deliberately kept, since
the digest did go out. The key carries a TTL as a backstop against a run
vanishing mid-send (a cancelled job, a runner lost), which would otherwise
leave the day claimed forever. It is longer than a day because the date in the
key, not the TTL, is what separates one day from the next.
"""

import logging
import sys

from src.kv_client import kv_configured, kv_delete, kv_set_if_absent
from src.logger import get_logger
from src.schedule_guard import now_local

logger = get_logger(__name__)

# Two days: long enough that an abandoned claim cannot be mistaken for today's
# while today is still running, short enough that the keys do not accumulate.
CLAIM_TTL_SECONDS = 172800


def claim_key(date_iso: str) -> str:
    return f"digest:claim:{date_iso}"


def claim_today(force: bool = False) -> bool:
    """Try to become the run that sends today's digest.

    Returns True when this run may send: it won the claim, `force` was asked
    for, or KV is not configured at all (a local run, where there is no second
    runner to race with and refusing to send would be the worse failure).
    """
    today = now_local().date().isoformat()

    if not kv_configured():
        logger.warning("KV is not configured — sending without a claim")
        return True

    if force:
        # An explicit instruction to send, so the claim is recorded rather than
        # consulted: whoever else held it today does not get a veto.
        kv_delete(claim_key(today))
        kv_set_if_absent(claim_key(today), {"forced": True}, CLAIM_TTL_SECONDS)
        logger.info("Forced send for %s", today)
        return True

    acquired = kv_set_if_absent(
        claim_key(today), {"at": now_local().isoformat()}, CLAIM_TTL_SECONDS
    )
    if acquired:
        logger.info("Claimed the digest for %s", today)
    else:
        logger.info("Another run already claimed %s — not sending", today)
    return acquired


def release_today() -> None:
    """Give up today's claim, so a later tick can retry the send."""
    if not kv_configured():
        return
    today = now_local().date().isoformat()
    kv_delete(claim_key(today))
    logger.info("Released the claim for %s", today)


def _log_to_stderr() -> None:
    """Send this process's logging to stderr.

    kv_client logs through the app logger, which writes to stdout, and the
    workflow captures this command's stdout into $GITHUB_OUTPUT. Anything but
    the decision on stdout would corrupt that value. A fresh handler replaces
    the configured ones rather than re-pointing them, so nothing outside this
    process's logging is left holding a stream it did not open.
    """
    app = logging.getLogger("ai_research_digest")
    for handler in list(app.handlers):
        app.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-8s | %(name)s | %(message)s"))
    app.addHandler(handler)


def main() -> int:
    """CLI: `claim [--force]` prints true/false, `release` gives the day back.

    `claim` exits 0 either way and reports on stdout, like schedule_guard's
    `check`, so the workflow branches on the value rather than on an exit code
    that would read as a step failure. Diagnostics go to stderr, because the
    workflow captures stdout straight into $GITHUB_OUTPUT.
    """
    _log_to_stderr()

    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]

    if len(args) != 1 or args[0] not in ("claim", "release"):
        print(
            "usage: python -m src.digest_claim {claim [--force]|release}",
            file=sys.stderr,
        )
        return 2

    if args[0] == "release":
        release_today()
        return 0

    print("true" if claim_today(force=force) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
