"""Tests that the digest workflow actually wires up the schedule guard.

src/schedule_guard.py was fully unit-tested and correct, and the digest still
sent four to five times a day for three days: the workflow called `check` but
never called `mark`, so last_daily_date was never written and every tick after
noon read as due. The same release keyed weekly routing off
github.event.schedule, which stopped matching the moment the two crons became
a single polling cron, so the weekly roundup never ran at all.

Neither bug was reachable from a unit test of the guard — both lived in the
YAML. These tests read the workflow itself, so the wiring is covered too.
"""

import re
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "daily-news.yml"


@pytest.fixture(scope="module")
def workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def executable(workflow: str) -> str:
    """The workflow with comment lines removed.

    The comments explain these very bugs by name, so a plain substring search
    matches the explanation as readily as a real regression.
    """
    return "\n".join(
        line for line in workflow.splitlines() if not line.lstrip().startswith("#")
    )


@pytest.fixture(scope="module")
def steps(workflow: str) -> list[str]:
    """Split the job into per-step blocks, each starting at '- name:'."""
    parts = re.split(r"\n(?=      - name:)", workflow)
    return [p for p in parts if p.lstrip().startswith("- name:")]


def _step_running(steps: list[str], command: str) -> str:
    matches = [s for s in steps if command in s]
    assert matches, f"no step runs {command!r}"
    assert len(matches) == 1, f"{len(matches)} steps run {command!r}, expected 1"
    return matches[0]


class TestMarking:
    """The bug: state was read but never written."""

    def test_a_step_marks_the_daily_run(self, steps):
        _step_running(steps, "src.schedule_guard mark daily")

    def test_a_step_marks_the_weekly_run(self, steps):
        _step_running(steps, "src.schedule_guard mark weekly")

    def test_daily_mark_is_gated_on_the_daily_decision(self, steps):
        step = _step_running(steps, "src.schedule_guard mark daily")
        assert "steps.guard.outputs.daily == 'true'" in step
        assert "outputs.weekly" not in step, "marking daily must not depend on weekly"

    def test_weekly_mark_is_gated_on_the_weekly_decision(self, steps):
        step = _step_running(steps, "src.schedule_guard mark weekly")
        assert "steps.guard.outputs.weekly == 'true'" in step
        assert "outputs.daily" not in step, "marking weekly must not depend on daily"

    def test_each_mark_comes_after_its_send(self, steps, workflow):
        """Marking before the send would record a run that never happened."""
        for send, mark in (("python main.py", "mark daily"),
                           ("python weekly_digest.py", "mark weekly")):
            assert workflow.index(send) < workflow.index(mark), (
                f"{mark!r} must come after {send!r}"
            )


class TestRouting:
    """The other bug: routing keyed off a cron string that no longer exists."""

    def test_daily_send_is_gated_on_the_guard(self, steps):
        step = _step_running(steps, "python main.py")
        assert "steps.guard.outputs.daily == 'true'" in step

    def test_weekly_send_is_gated_on_the_guard(self, steps):
        step = _step_running(steps, "python weekly_digest.py")
        assert "steps.guard.outputs.weekly == 'true'" in step

    def test_routing_does_not_depend_on_which_cron_fired(self, executable):
        """github.event.schedule is empty for manual dispatch and changes
        whenever the cron is edited, so it must not decide what runs."""
        assert "github.event.schedule" not in executable

    def test_no_stale_cron_string_comparison(self, executable):
        """A literal cron in a shell test silently stops matching when the
        schedule is edited — exactly how the weekly roundup went missing."""
        assert not re.search(r'"\d+ \d+ \* \* \d+"', executable)


class TestGuardContract:
    """The check step feeds $GITHUB_OUTPUT, which the guard's CLI relies on."""

    def test_check_writes_both_decisions_to_github_output(self, steps):
        step = _step_running(steps, "src.schedule_guard check daily")
        assert 'daily=$(python3 -m src.schedule_guard check daily)' in step
        assert 'weekly=$(python3 -m src.schedule_guard check weekly)' in step
        assert "$GITHUB_OUTPUT" in step

    def test_state_file_is_committed(self, steps):
        """An uncommitted mark is forgotten, and the day repeats."""
        step = _step_running(steps, "git add")
        assert "data/" in step

    def test_expensive_steps_are_gated_so_no_op_ticks_stay_cheap(self, steps):
        for command in ("pip install -r requirements.txt", "actions/setup-python"):
            step = _step_running(steps, command)
            assert "steps.guard.outputs" in step, (
                f"{command!r} must not run on a tick with nothing due"
            )
