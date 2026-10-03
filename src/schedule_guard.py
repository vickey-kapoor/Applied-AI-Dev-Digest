"""Decide whether the daily digest is due, and whether to wait for it.

GitHub's scheduled delivery is best-effort: measured on this repo, a single
daily cron arrived between 30 minutes and 5h23m after its slot, which put the
digest anywhere from late morning to evening. Firing a cheap hourly poll and
running the digest on the first poll that lands after the target local time
converts that into "within roughly an hour of noon", because a delayed poll is
simply followed by another one.

That still only gets the digest out *after* noon, and measured sends landed
from 12:05 to 16:41 local. The lateness is in the delivery, not the schedule,
so no cron interval fixes it — but a poll that lands *before* noon can simply
hold. `seconds_until_target` is that second half: a tick arriving in the hours
before the target waits for it and sends on the minute, so any honoured morning
tick pins the digest to noon exactly. The wait is capped, because a tick that
lands at 02:00 should not hold a runner for ten hours; past the cap the tick
exits as it always did and a later one carries the day.

A dispatch from an external scheduler, which GitHub delivers immediately, is
the reliable version of the same idea; the README's Scheduling section covers
it. This is what the repo can do unaided.

The poll ran every 15 minutes at first. GitHub honoured about one tick in
twelve at that rate — measured gaps of 1.5 to 4.5 hours — so the finer
interval bought nothing and asking for less appears to get more.

The target is evaluated in America/Chicago rather than a fixed UTC hour, so the
digest stays at local noon when CDT gives way to CST in November. A UTC cron
cannot do that on its own.

State lives in data/schedule_state.json, which the workflow commits alongside
the digest output. A run that sends but fails to commit would let the next poll
run again; main.py already filters items sent as a previous top pick, so that
repeat finds nothing new and sends nothing.

There is one job. A Sunday roundup used to share this guard, which is why the
job name survives in the state keys and the CLI: dropping the argument would
have made every stored `last_daily_date` unreadable for nothing.
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Local time the digest should land. Evaluated in this zone, so the wall-clock
# time holds across daylight-saving transitions.
DIGEST_TIMEZONE = ZoneInfo(os.getenv("DIGEST_TIMEZONE", "America/Chicago"))
DAILY_TARGET_HOUR = int(os.getenv("DAILY_TARGET_HOUR", "12"))

# Longest a tick will hold a runner waiting for the target hour. Three hours
# covers a tick honoured any time from 09:00 local, which is most of the
# morning, without letting a 02:00 tick sit for ten. Jobs are free on public
# repositories, but GitHub kills one at six hours regardless.
DAILY_MAX_WAIT_SECONDS = int(os.getenv("DAILY_MAX_WAIT_SECONDS", "10800"))

# Added to the computed wait. `is_due` compares whole hours, so landing at
# 11:59:59 after a sleep that rounded down would read as not due and waste the
# tick entirely.
WAIT_OVERSHOOT_SECONDS = 30

STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "schedule_state.json"
)

JOBS = ("daily",)


def load_state(path: str | None = None) -> dict:
    """Read the last-run record, treating any problem as 'nothing has run'.

    The path resolves at call time rather than binding STATE_PATH as a default,
    so tests and callers can redirect it.
    """
    path = path or STATE_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict, path: str | None = None) -> None:
    """Write the last-run record."""
    path = path or STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def is_due(job: str, now_local: datetime, state: dict) -> bool:
    """Whether `job` should run at `now_local`, given what has already run.

    Due when the local target hour has passed today and today's run has not
    happened.
    """
    if job not in JOBS:
        raise ValueError(f"Unknown job: {job!r}")

    if now_local.hour < DAILY_TARGET_HOUR:
        return False

    return state.get(f"last_{job}_date") != now_local.date().isoformat()


def seconds_until_target(
    job: str,
    now_local: datetime,
    state: dict,
    max_wait: int | None = None,
) -> int:
    """How long to hold before `job` becomes due, or 0 for "do not hold".

    Zero when the target has already passed, when today's run already
    happened, or when the wait would exceed `max_wait` — in each of those a
    tick should go on and let `is_due` decide.
    """
    if job not in JOBS:
        raise ValueError(f"Unknown job: {job!r}")

    if max_wait is None:
        max_wait = DAILY_MAX_WAIT_SECONDS

    if state.get(f"last_{job}_date") == now_local.date().isoformat():
        return 0

    target = now_local.replace(
        hour=DAILY_TARGET_HOUR, minute=0, second=0, microsecond=0
    )
    gap = (target - now_local).total_seconds()
    if gap <= 0 or gap > max_wait:
        return 0

    return int(gap) + WAIT_OVERSHOOT_SECONDS


def mark_ran(job: str, now_local: datetime, state: dict) -> dict:
    """Return a copy of `state` recording that `job` ran on `now_local`'s date."""
    updated = dict(state)
    updated[f"last_{job}_date"] = now_local.date().isoformat()
    updated[f"last_{job}_at"] = now_local.isoformat()
    return updated


def now_local() -> datetime:
    return datetime.now(DIGEST_TIMEZONE)


def main() -> int:
    """CLI: `check` prints true/false, `sleep` prints seconds, `mark` records.

    `check` always exits 0 and reports the decision on stdout, so the workflow
    can branch on the value rather than on an exit code that would read as a
    step failure.
    """
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "mark", "sleep"):
        print(
            "usage: python -m src.schedule_guard {check|mark|sleep} daily",
            file=sys.stderr,
        )
        return 2

    command, job = sys.argv[1], sys.argv[2]
    if job not in JOBS:
        print(f"unknown job: {job}", file=sys.stderr)
        return 2

    current = now_local()
    state = load_state()

    if command == "check":
        due = is_due(job, current, state)
        # Diagnostics go to stderr and the decision to stdout, because the
        # workflow captures stdout with $(...) straight into $GITHUB_OUTPUT.
        # Anything else on stdout would corrupt that value.
        print(
            f"{job} due={due} at {current:%Y-%m-%d %H:%M %Z} "
            f"(target {DAILY_TARGET_HOUR:02d}:00, "
            f"last run {state.get(f'last_{job}_date', 'never')})",
            file=sys.stderr,
        )
        print("true" if due else "false")
        return 0

    if command == "sleep":
        wait = seconds_until_target(job, current, state)
        print(
            f"{job} wait={wait}s at {current:%Y-%m-%d %H:%M %Z} "
            f"(target {DAILY_TARGET_HOUR:02d}:00, cap {DAILY_MAX_WAIT_SECONDS}s)",
            file=sys.stderr,
        )
        print(wait)
        return 0

    save_state(mark_ran(job, current, state))
    print(f"Recorded {job} run for {current.date().isoformat()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
