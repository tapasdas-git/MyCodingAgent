from __future__ import annotations

from pathlib import Path

import pytest

from mycodeagent.config import WorkflowConfig
from mycodeagent.errors import AgentExecutionError
from mycodeagent.models import (
    ActionDecision, AgentResult, AgentRole, ExecutionMemory, ReviewDecision, ReviewFinding,
    ReviewResult, SupervisorAction, TestResult as AgentTestResult, WorkflowState,
)
from mycodeagent.orchestrator import SupervisorOrchestrator
from mycodeagent.validator import WorkspaceValidator


class FakeExecutor:
    def __init__(self, root: Path, review_failures: int = 0):
        self.root = root
        self.review_failures = review_failures
        self.reviews = 0

    def supervisor_decision(self, memory, available):
        choice = {
            WorkflowState.WORKING: SupervisorAction.IMPLEMENT,
            WorkflowState.IMPLEMENTING: SupervisorAction.VALIDATE,
            WorkflowState.TESTING: SupervisorAction.RUN_TESTS,
            WorkflowState.REVIEWING: SupervisorAction.REVIEW,
            WorkflowState.CHANGES_REQUESTED: SupervisorAction.REMEDIATE,
            WorkflowState.APPROVED: SupervisorAction.FINISH,
        }[memory.state]
        assert choice in available
        return ActionDecision(choice, "test decision")

    def invoke_role(self, role, memory, request, progress=None):
        if progress:
            progress("agent.attempt.started", "running", {"attempt": 1})
        if role is AgentRole.IMPLEMENTER:
            for relative in memory.task.required_files:
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("value = 1\n", encoding="utf-8")
        if role is AgentRole.REVIEWER:
            self.reviews += 1
        return AgentResult(role, "completed", "done", raw_output="review")

    def parse_review(self, output, fingerprint):
        if self.reviews <= self.review_failures:
            finding = ReviewFinding("R1", "blocking", "Acceptance gap", "Implement missing behavior")
            return ReviewResult(ReviewDecision.CHANGES_REQUESTED, fingerprint, (finding,), "fix")
        return ReviewResult(ReviewDecision.APPROVED, fingerprint, (), "approved")


class PassingTests:
    def __init__(self, root: Path):
        self.root = root

    def run(self, worktree, task):
        fingerprint = WorkspaceValidator(self.root, task).fingerprint()
        return AgentTestResult(("pytest",), 0, True, "passed", "", 0.01, fingerprint)


class MalformedSupervisorExecutor:
    role_invoked = False

    def supervisor_decision(self, memory, available):
        raise AgentExecutionError("Supervisor returned an invalid action")

    def invoke_role(self, role, memory, request, progress=None):
        self.role_invoked = True
        raise AssertionError("No role should be invoked after supervisor failure")


def config() -> WorkflowConfig:
    return WorkflowConfig("codex", "model", "high", 60, 5, {})


def run_flow(git_repo, task, review_failures):
    executor = FakeExecutor(git_repo, review_failures)
    supervisor = SupervisorOrchestrator(git_repo, config(), executor, create_worktree=False)
    supervisor.tests = PassingTests(git_repo)
    return supervisor.run(task), executor


def test_approved_flow_completes_locally_after_one_cycle(git_repo, task):
    memory, executor = run_flow(git_repo, task, 0)
    assert memory.state is WorkflowState.COMPLETED
    assert memory.cycle == 1
    assert executor.reviews == 1
    human_log = (git_repo / "logs" / f"{task.task_id}.log").read_text()
    assert "Implementation started" in human_log
    assert "Implementation completed" in human_log
    assert "Scope validation passed" in human_log
    assert "Tests passed" in human_log
    assert "Review approved" in human_log
    assert "Workflow completed successfully" in human_log


def test_review_context_routes_back_to_implementer_then_rereviews(git_repo, task):
    memory, executor = run_flow(git_repo, task, 1)
    assert memory.state is WorkflowState.COMPLETED
    assert memory.cycle == 2
    assert executor.reviews == 2
    implement_calls = [value for value in memory.agent_results if value["role"] == "implementer"]
    assert len(implement_calls) == 2


def test_supervisor_parse_failure_is_persisted_as_failed(git_repo, task):
    executor = MalformedSupervisorExecutor()
    supervisor = SupervisorOrchestrator(git_repo, config(), executor, create_worktree=False)
    memory = supervisor.run(task)

    assert memory.state is WorkflowState.FAILED
    assert memory.cycle == 0
    assert not executor.role_invoked
    assert memory.errors == [{
        "stage": "supervisor",
        "cycle": 0,
        "message": "Supervisor returned an invalid action",
    }]

    persisted = supervisor.state.load_json(supervisor.state.run_dir(memory.run_id) / "memory.json")
    assert persisted["state"] == "failed"
    assert persisted["errors"] == memory.errors


def test_exploration_is_available_only_until_context_exists(task):
    memory = ExecutionMemory("run", task, state=WorkflowState.WORKING)
    assert SupervisorAction.EXPLORE in SupervisorOrchestrator.available_actions(memory, deliver=False)

    memory.repository_context = {"summary": "inspected"}
    assert SupervisorAction.EXPLORE not in SupervisorOrchestrator.available_actions(memory, deliver=False)
    assert SupervisorAction.IMPLEMENT in SupervisorOrchestrator.available_actions(memory, deliver=False)


def test_implementer_cannot_complete_before_required_coding_artifacts_exist(git_repo, task):
    memory = ExecutionMemory("run", task, worktree=str(git_repo))

    with pytest.raises(AgentExecutionError, match="returned before creating required artifact"):
        SupervisorOrchestrator._assert_role_artifacts(AgentRole.IMPLEMENTER, memory)


def test_reviewer_context_contains_deterministic_change_evidence(git_repo, task):
    changed = git_repo / task.required_files[0]
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("value = 1\n", encoding="utf-8")
    memory = ExecutionMemory("run", task, worktree=str(git_repo))

    context = SupervisorOrchestrator._review_context(memory)

    evidence = context["change_evidence"]
    assert task.required_files[0] in evidence["changed_files"]
    assert evidence["untracked_file_contents"][task.required_files[0]] == "value = 1\n"
