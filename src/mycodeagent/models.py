"""Provider-neutral contracts for the hierarchical agent workflow."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class TaskSource(StrEnum):
    TODO = "todo"
    GITHUB = "github"
    DIRECT = "direct"


class TaskIntent(StrEnum):
    FEATURE = "feature"
    BUG_FIX = "bug_fix"
    REFACTOR = "refactor"
    TEST = "test"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    INVESTIGATION = "investigation"
    UNKNOWN = "unknown"


class AgentRole(StrEnum):
    EXPLORER = "explorer"
    IMPLEMENTER = "implementer"
    TEST_WRITER = "test_writer"
    REVIEWER = "reviewer"


class SupervisorAction(StrEnum):
    EXPLORE = "explore_repository"
    IMPLEMENT = "implement_task"
    WRITE_TESTS = "write_tests"
    VALIDATE = "validate_scope"
    RUN_TESTS = "run_tests"
    REVIEW = "request_review"
    REMEDIATE = "implement_remediation"
    DELIVER = "create_pr"
    REQUEST_INPUT = "request_user_input"
    FINISH = "finish"
    FAIL = "fail_safely"


class WorkflowState(StrEnum):
    READY = "ready"
    WORKING = "working"
    IMPLEMENTING = "implementing"
    VALIDATING = "validating"
    TESTING = "testing"
    REVIEWING = "reviewing"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    COMPLETED = "completed"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    NEEDS_INPUT = "needs_input"
    FAILED = "failed"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class WorkspaceBoundary:
    root: str
    coding_dir: str
    test_dir: str
    requirements_file: str | None = None

    def allowed_write_paths(self) -> tuple[str, str]:
        return (self.coding_dir, self.test_dir)


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    source: TaskSource
    source_reference: str
    state: str
    priority: str
    title: str
    intent: TaskIntent
    outcome: str
    repository: str | None
    dependencies: tuple[str, ...]
    architecture_requirements: tuple[str, ...]
    security_requirements: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    required_files: tuple[str, ...]
    workspace: WorkspaceBoundary
    raw_section: str
    delivery_requested: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source"] = self.source.value
        value["intent"] = self.intent.value
        return value


@dataclass(frozen=True)
class AgentRoleConfig:
    role: AgentRole
    harness: str
    model: str
    effort: str
    timeout_seconds: int
    read_only: bool
    write_scope: str | None = None


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    severity: str
    explanation: str
    recommended_fix: str
    requirement: str = ""
    file: str | None = None
    line: int | None = None


@dataclass(frozen=True)
class ReviewResult:
    decision: ReviewDecision
    reviewed_fingerprint: str
    findings: tuple[ReviewFinding, ...] = ()
    summary: str = ""


@dataclass(frozen=True)
class TestResult:
    command: tuple[str, ...]
    exit_code: int
    passed: bool
    stdout: str
    stderr: str
    duration_seconds: float
    fingerprint: str


@dataclass(frozen=True)
class AgentResult:
    role: AgentRole
    status: str
    summary: str
    changed_files: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    raw_output: str = ""


@dataclass(frozen=True)
class ActionDecision:
    action: SupervisorAction
    rationale: str
    # Derived deterministically from action; never trusted from model output.
    role: AgentRole | None = None


@dataclass
class ExecutionMemory:
    run_id: str
    task: TaskSpec
    state: WorkflowState = WorkflowState.READY
    cycle: int = 0
    max_cycles: int = 5
    worktree: str | None = None
    base_commit: str | None = None
    current_fingerprint: str = ""
    repository_context: dict[str, Any] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    agent_results: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    review_results: list[dict[str, Any]] = field(default_factory=list)
    unresolved_findings: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task.to_dict(),
            "state": self.state.value,
            "cycle": self.cycle,
            "max_cycles": self.max_cycles,
            "worktree": self.worktree,
            "base_commit": self.base_commit,
            "current_fingerprint": self.current_fingerprint,
            "repository_context": self.repository_context,
            "observations": self.observations,
            "decisions": self.decisions,
            "agent_results": self.agent_results,
            "test_results": self.test_results,
            "review_results": self.review_results,
            "unresolved_findings": self.unresolved_findings,
            "artifacts": self.artifacts,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    fingerprint: str = ""


def relative_path(path: Path, root: Path) -> str:
    """Return a stable POSIX repository-relative path."""
    return path.resolve().relative_to(root.resolve()).as_posix()
