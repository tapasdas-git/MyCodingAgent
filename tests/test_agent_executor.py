import json
import subprocess
from types import SimpleNamespace

import pytest

from mycodeagent.agent_executor import OmnigentAgentExecutor
from mycodeagent.errors import AgentExecutionError
from mycodeagent.models import AgentRole, ReviewDecision, SupervisorAction


def test_structured_review_context_is_preserved():
    output = '''{"decision":"CHANGES_REQUESTED","summary":"gap","findings":[{"finding_id":"R1","severity":"blocking","explanation":"missing export","recommended_fix":"export it","requirement":"public API","file":"Coding/__init__.py","line":1}]}'''
    review = OmnigentAgentExecutor.parse_review(output, "sha256:abc")
    assert review.decision is ReviewDecision.CHANGES_REQUESTED
    assert review.reviewed_fingerprint == "sha256:abc"
    assert review.findings[0].file == "Coding/__init__.py"


def test_supervisor_ignores_main_role_and_derives_implementer():
    output = json.dumps({
        "action": "implement_task",
        "role": "main",
        "rationale": "The task is ready",
    })
    decision = OmnigentAgentExecutor.parse_supervisor_decision(
        output, (SupervisorAction.IMPLEMENT,)
    )
    assert decision.action is SupervisorAction.IMPLEMENT
    assert decision.role is AgentRole.IMPLEMENTER


@pytest.mark.parametrize(
    ("action", "expected_role"),
    [
        (SupervisorAction.EXPLORE, AgentRole.EXPLORER),
        (SupervisorAction.WRITE_TESTS, AgentRole.TEST_WRITER),
        (SupervisorAction.REVIEW, AgentRole.REVIEWER),
        (SupervisorAction.REMEDIATE, AgentRole.IMPLEMENTER),
        (SupervisorAction.VALIDATE, None),
        (SupervisorAction.RUN_TESTS, None),
        (SupervisorAction.FINISH, None),
    ],
)
def test_supervisor_role_is_derived_from_action(action, expected_role):
    output = json.dumps({"action": action.value, "rationale": "next"})
    decision = OmnigentAgentExecutor.parse_supervisor_decision(output, (action,))
    assert decision.role is expected_role


def test_supervisor_rejects_invalid_action():
    with pytest.raises(AgentExecutionError, match="invalid action"):
        OmnigentAgentExecutor.parse_supervisor_decision(
            '{"action":"not-real"}', (SupervisorAction.IMPLEMENT,)
        )


def test_supervisor_rejects_disallowed_action():
    with pytest.raises(AgentExecutionError, match="disallowed action"):
        OmnigentAgentExecutor.parse_supervisor_decision(
            '{"action":"request_review"}', (SupervisorAction.IMPLEMENT,)
        )


def test_transient_runner_disconnect_is_retried_once(monkeypatch, tmp_path):
    definition = tmp_path / "implementer.yaml"
    definition.write_text("name: test\n", encoding="utf-8")
    results = iter([
        SimpleNamespace(returncode=1, stdout="", stderr="Runner disconnected unexpectedly."),
        SimpleNamespace(returncode=0, stdout="completed", stderr=""),
    ])
    calls = []

    class FakeProcess:
        pid = 123

        def __init__(self, result):
            self.result = result
            self.returncode = result.returncode

        def communicate(self, timeout=None):
            return self.result.stdout, self.result.stderr

    def fake_popen(*args, **kwargs):
        calls.append(args)
        return FakeProcess(next(results))

    monkeypatch.setattr("mycodeagent.agent_executor.subprocess.Popen", fake_popen)
    executor = OmnigentAgentExecutor(tmp_path, None, tmp_path)

    output = executor._run_agent(
        definition, harness="codex", model="model", effort="high",
        timeout=60, prompt="{}", cwd=tmp_path,
    )

    assert output == "completed"
    assert len(calls) == 2


def test_non_transient_agent_failure_is_not_retried(monkeypatch, tmp_path):
    definition = tmp_path / "implementer.yaml"
    definition.write_text("name: test\n", encoding="utf-8")
    calls = []

    class FakeProcess:
        pid = 123
        returncode = 1

        def communicate(self, timeout=None):
            return "", "invalid model"

    def fake_popen(*args, **kwargs):
        calls.append(args)
        return FakeProcess()

    monkeypatch.setattr("mycodeagent.agent_executor.subprocess.Popen", fake_popen)
    executor = OmnigentAgentExecutor(tmp_path, None, tmp_path)

    with pytest.raises(AgentExecutionError, match="after 1 attempt"):
        executor._run_agent(
            definition, harness="codex", model="model", effort="high",
            timeout=60, prompt="{}", cwd=tmp_path,
        )

    assert len(calls) == 1


def test_timeout_terminates_process_group_and_reports_total_budget(monkeypatch, tmp_path):
    definition = tmp_path / "implementer.yaml"
    definition.write_text("name: test\n", encoding="utf-8")
    signals = []

    class TimedOutProcess:
        pid = 456
        returncode = None
        calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("omnigent", timeout)
            return "", ""

    monkeypatch.setattr(
        "mycodeagent.agent_executor.subprocess.Popen",
        lambda *args, **kwargs: TimedOutProcess(),
    )
    monkeypatch.setattr(
        "mycodeagent.agent_executor.os.killpg",
        lambda pid, value: signals.append((pid, value)),
    )
    executor = OmnigentAgentExecutor(tmp_path, None, tmp_path)

    with pytest.raises(AgentExecutionError, match="total retry budget"):
        executor._run_agent(
            definition, harness="codex", model="model", effort="high",
            timeout=60, prompt="{}", cwd=tmp_path,
        )

    assert signals[0][0] == 456
