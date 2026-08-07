"""Deterministic, approval-gated Git commit, push, and pull-request delivery."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .errors import ValidationError
from .models import ExecutionMemory, WorkflowState
from .validator import WorkspaceValidator


class PullRequestDelivery:
    def deliver(self, memory: ExecutionMemory) -> str:
        if memory.state is not WorkflowState.DELIVERING:
            raise ValidationError("Pull request delivery requires the approval-gated DELIVERING state")
        worktree = Path(memory.worktree or ".").resolve()
        validation = WorkspaceValidator(worktree, memory.task).validate()
        if not validation.passed:
            raise ValidationError("Pre-delivery validation failed: " + "; ".join(validation.errors))
        if validation.fingerprint != memory.current_fingerprint:
            raise ValidationError("Files changed after final review; approval fingerprint is stale")
        self._validate_repository(worktree, memory.task.repository)

        self._run(worktree, "git", "add", "--", memory.task.workspace.coding_dir, memory.task.workspace.test_dir)
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree, check=False)
        if staged.returncode == 1:
            self._run(worktree, "git", "commit", "-m", f"feat({memory.task.task_id}): {memory.task.title}")
        elif staged.returncode != 0:
            raise ValidationError("Could not inspect staged task changes")

        branch = self._run(worktree, "git", "branch", "--show-current").strip()
        if not branch:
            raise ValidationError("Delivery requires a named feature branch")
        self._run(worktree, "git", "push", "-u", "origin", branch)
        return self._run(
            worktree, "gh", "pr", "create", "--head", branch,
            "--title", f"feat({memory.task.task_id}): {memory.task.title}",
            "--body", self._body(memory),
        ).strip()

    @classmethod
    def _validate_repository(cls, worktree: Path, expected: str | None) -> None:
        if not expected:
            return
        actual = cls._run(worktree, "git", "remote", "get-url", "origin").strip()
        if cls._repository_name(actual) != cls._repository_name(expected):
            raise ValidationError(
                f"Task repository '{expected}' does not match origin remote '{actual}'"
            )

    @staticmethod
    def _repository_name(value: str) -> str:
        normalized = value.rstrip("/").removesuffix(".git")
        return normalized.rsplit("/", 1)[-1].rsplit(":", 1)[-1].lower()

    @staticmethod
    def _body(memory: ExecutionMemory) -> str:
        return (
            f"Automated MyCodeAgent delivery for `{memory.task.task_id}`.\n\n"
            f"- Workflow cycles: {memory.cycle}/{memory.max_cycles}\n"
            f"- Approved fingerprint: `{memory.current_fingerprint}`\n"
            "- Deterministic tests: passed\n"
            "- Final review: APPROVED\n"
        )

    @staticmethod
    def _run(cwd: Path, *command: str) -> str:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ValidationError(f"{' '.join(command)} failed: {detail}")
        return result.stdout
