"""Decide whether a scheduled digest is due.

GitHub's scheduled delivery is best-effort: measured on this repo, a single
daily cron arrived between 30 minutes and 5h23m after its slot, which put the
"daily" digest anywhere from late morning to evening. Firing a cheap hourly
poll and running the digest on the first poll that lands after the target local
time converts that into "within roughly an hour of noon", because a delayed
poll is simply followed by another one.

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
WEEKLY_TARGET_HOUR = int(os.getenv("WEEKLY_TARGET_HOUR", "13"))

# Sunday, matching datetime.isoweekday().
WEEKLY_ISOWEEKDAY = 7

STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "schedule_state.json"
)

JOBS = ("daily", "weekly")


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


def _target_hour(job: str) -> int:
    return WEEKLY_TARGET_HOUR if job == "weekly" else DAILY_TARGET_HOUR


def is_due(job: str, now_local: datetime, state: dict) -> bool:
    """Whether `job` should run at `now_local`, given what has already run.

    Due when the local target hour has passed today and today's run has not
    happened. The weekly roundup additionally requires it to be Sunday.
    """
    if job not in JOBS:
        raise ValueError(f"Unknown job: {job!r}")

    if job == "weekly" and now_local.isoweekday() != WEEKLY_ISOWEEKDAY:
        return False

    if now_local.hour < _target_hour(job):
        return False

    return state.get(f"last_{job}_date") != now_local.date().isoformat()


def mark_ran(job: str, now_local: datetime, state: dict) -> dict:
    """Return a copy of `state` recording that `job` ran on `now_local`'s date."""
    updated = dict(state)
    updated[f"last_{job}_date"] = now_local.date().isoformat()
    updated[f"last_{job}_at"] = now_local.isoformat()
    return updated


def now_local() -> datetime:
    return datetime.now(DIGEST_TIMEZONE)


def main() -> int:
    """CLI: `check <job>` prints true/false; `mark <job>` records a run.

    `check` always exits 0 and reports the decision on stdout, so the workflow
    can branch on the value rather than on an exit code that would read as a
    step failure.
    """
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "mark"):
        print("usage: python -m src.schedule_guard {check|mark} {daily|weekly}", file=sys.stderr)
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
            f"(target {_target_hour(job):02d}:00, "
            f"last run {state.get(f'last_{job}_date', 'never')})",
            file=sys.stderr,
        )
        print("true" if due else "false")
        return 0

    save_state(mark_ran(job, current, state))
    print(f"Recorded {job} run for {current.date().isoformat()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
