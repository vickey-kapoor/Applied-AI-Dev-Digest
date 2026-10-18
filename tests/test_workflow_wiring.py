"""Tests that the digest workflow actually wires up the schedule guard.

src/schedule_guard.py was fully unit-tested and correct, and the digest still
sent four to five times a day for three days: the workflow called `check` but
never called `mark`, so last_daily_date was never written and every tick after
noon read as due. A companion bug keyed routing off github.event.schedule,
which stopped matching the moment two crons became a single polling cron.

Neither bug was reachable from a unit test of the guard — both lived in the
YAML. These tests read the workflow itself, so the wiring is covered too.

The workflow sends one digest a day and nothing else, so these tests also pin
that no second job has crept back into it.
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

    def test_daily_mark_is_gated_on_the_daily_decision(self, steps):
        step = _step_running(steps, "src.schedule_guard mark daily")
        assert "steps.guard.outputs.daily == 'true'" in step

    def test_the_mark_comes_after_the_send(self, workflow):
        """Marking before the send would record a run that never happened."""
        assert workflow.index("python main.py") < workflow.index("mark daily"), (
            "'mark daily' must come after 'python main.py'"
        )


class TestRouting:
    """The other bug: routing keyed off a cron string that no longer exists."""

    def test_daily_send_is_gated_on_the_guard(self, steps):
        step = _step_running(steps, "python main.py")
        assert "steps.guard.outputs.daily == 'true'" in step

    def test_routing_does_not_depend_on_which_cron_fired(self, executable):
        """github.event.schedule is empty for manual dispatch and changes
        whenever the cron is edited, so it must not decide what runs."""
        assert "github.event.schedule" not in executable

    def test_no_stale_cron_string_comparison(self, executable):
        """A literal cron in a shell test silently stops matching when the
        schedule is edited — exactly how a second job once went missing."""
        assert not re.search(r'"\d+ \d+ \* \* \d+"', executable)


class TestDispatchIsGuarded:
    """An external scheduler dispatches this workflow at noon local time.

    Dispatch used to mean "send, whatever the guard says", which was fine while
    the only caller was a person clicking Run workflow. Once a scheduler calls
    it every day, that bypass would send a second digest on any day the hourly
    poll got there first. So a dispatch runs the guard like a tick does, and
    only the explicit `force` input skips it.
    """

    def test_dispatch_accepts_a_force_input(self, executable):
        assert "force:" in executable, "workflow_dispatch needs a force input"

    def test_force_defaults_to_off(self, executable):
        assert "default: false" in executable

    def test_the_guard_decides_unless_force_is_set(self, steps):
        step = _step_running(steps, "src.schedule_guard check daily")
        assert "inputs.force" in step, "the bypass must key off force"
        assert "github.event_name" not in step, (
            "being a dispatch is not itself a reason to skip the guard"
        )


class TestHoldingForTheTarget:
    """The hold is what moves the digest from "after noon" to "at noon"."""

    def test_a_step_holds_for_the_target(self, steps):
        _step_running(steps, "src.schedule_guard sleep daily")

    def test_the_hold_comes_before_the_due_check(self, workflow):
        """Holding after the check would read the decision made too early."""
        assert workflow.index("sleep daily") < workflow.index("check daily")

    def test_only_scheduled_ticks_hold(self, steps):
        """A dispatch is already at the target, or is a person wanting it now;
        either way it must not sit for hours."""
        step = _step_running(steps, "src.schedule_guard sleep daily")
        assert "github.event_name == 'schedule'" in step

    def test_the_job_outlives_the_longest_hold(self, executable):
        """A job timeout below the wait cap would kill the tick mid-hold."""
        import re

        match = re.search(r"timeout-minutes: (\d+)", executable)
        assert match, "the job needs a timeout"
        assert int(match.group(1)) > 180, "3h of holding needs more than 3h of job"


class TestGuardContract:
    """The check step feeds $GITHUB_OUTPUT, which the guard's CLI relies on."""

    def test_check_writes_the_decision_to_github_output(self, steps):
        step = _step_running(steps, "src.schedule_guard check daily")
        assert 'daily=$(python3 -m src.schedule_guard check daily)' in step
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


class TestOneDigestADay:
    """The digest is daily only. The Sunday roundup was removed deliberately.

    It would come back as a quiet regression: a `weekly` branch in the guard
    reads as false forever rather than failing, so nothing would notice.
    """

    def test_the_workflow_does_not_run_a_second_digest(self, executable):
        assert "weekly" not in executable.lower()

    def test_no_weekly_script_remains(self):
        assert not (WORKFLOW.parent.parent.parent / "weekly_digest.py").exists()

    def test_the_guard_knows_only_the_daily_job(self):
        from src.schedule_guard import JOBS

        assert JOBS == ("daily",)


class TestModelChoiceIsAWorkflowSetting:
    """gpt-4o-mini shuts down on 14-Jan-2027, so a replacement has to be
    tried in production — no CI job can make a live call to prove one
    behaves. These are repository variables rather than secrets or code so
    that trying one, and changing back, are both a settings edit.
    """

    def test_the_send_step_passes_the_model_variables(self, steps):
        send = _step_running(steps, "python main.py")
        for name in (
            "OPENAI_MODEL",
            "OPENAI_MODEL_RANKING",
            "OPENAI_MODEL_SUMMARY",
            "OPENAI_REASONING_EFFORT",
        ):
            assert f"{name}: ${{{{ vars.{name} }}}}" in send

    def test_they_are_variables_rather_than_secrets(self, steps):
        """A model name is not a credential, and a secret cannot be read back
        to see which model a run actually used."""
        send = _step_running(steps, "python main.py")
        assert "secrets.OPENAI_MODEL_RANKING" not in send

    def _constants_with(self, monkeypatch, **env):
        import importlib

        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return importlib.reload(importlib.import_module("src.constants"))

    def teardown_method(self):
        import importlib

        importlib.reload(importlib.import_module("src.constants"))

    def test_an_unset_variable_leaves_the_code_default_in_place(self, monkeypatch):
        """GitHub passes an unset variable as an empty string, which a
        getenv default would not catch."""
        constants = self._constants_with(
            monkeypatch,
            OPENAI_MODEL="",
            OPENAI_MODEL_RANKING="",
            OPENAI_MODEL_SUMMARY="",
            OPENAI_REASONING_EFFORT="",
        )
        assert constants.OPENAI_MODEL_RANKING == "gpt-6.1-sol"
        assert constants.OPENAI_MODEL_SUMMARY == "gpt-6-luna"
        assert constants.OPENAI_REASONING_EFFORT is None

    def test_the_two_steps_default_to_different_models(self, monkeypatch):
        """Ranking is the editorial judgement and the only call whose mistakes
        the reader sees as a bad pick; the summary extracts from one article
        the ranker already chose. One model for both was the old shape."""
        constants = self._constants_with(
            monkeypatch, OPENAI_MODEL="", OPENAI_MODEL_RANKING="", OPENAI_MODEL_SUMMARY=""
        )
        assert constants.OPENAI_MODEL_RANKING != constants.OPENAI_MODEL_SUMMARY

    def test_neither_default_is_the_model_being_switched_off(self, monkeypatch):
        """gpt-4o-mini shuts down on 14-Jan-2027."""
        constants = self._constants_with(
            monkeypatch, OPENAI_MODEL="", OPENAI_MODEL_RANKING="", OPENAI_MODEL_SUMMARY=""
        )
        assert "gpt-4o-mini" not in (
            constants.OPENAI_MODEL_RANKING,
            constants.OPENAI_MODEL_SUMMARY,
        )

    def test_one_variable_rolls_both_steps_back(self, monkeypatch):
        """The rollback has to be one edit, not a race to remember both names."""
        constants = self._constants_with(
            monkeypatch,
            OPENAI_MODEL="gpt-4o-mini",
            OPENAI_MODEL_RANKING="",
            OPENAI_MODEL_SUMMARY="",
        )
        assert constants.OPENAI_MODEL_RANKING == "gpt-4o-mini"
        assert constants.OPENAI_MODEL_SUMMARY == "gpt-4o-mini"

    def test_a_per_step_variable_beats_the_shared_one(self, monkeypatch):
        constants = self._constants_with(
            monkeypatch, OPENAI_MODEL="gpt-4o-mini", OPENAI_MODEL_RANKING="gpt-6-astra"
        )
        assert constants.OPENAI_MODEL_RANKING == "gpt-6-astra"
        assert constants.OPENAI_MODEL_SUMMARY == "gpt-4o-mini"
