"""Git worktree isolation and safe task-workspace resolution."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ValidationError
from .models import TaskSpec

CLEANUP_ONLY_PREFIXES = (".codex-tmp/", ".mycodeagent/", "logs/")


@dataclass(frozen=True)
class WorktreeContext:
    path: Path
    branch: str
    base_commit: str


class WorktreeManager:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()

    def create(self, task: TaskSpec) -> WorktreeContext:
        slug = re.sub(r"[^a-z0-9-]+", "-", task.task_id.lower()).strip("-")
        branch = f"feature/{slug}"
        worktree = self.worktree_path(task)
        if worktree.exists():
            registered = self._git("worktree", "list", "--porcelain")
            if f"worktree {worktree}" not in registered:
                raise ValidationError(f"Existing path is not a registered worktree: {worktree}")
            current_branch = self._git_at(worktree, "branch", "--show-current")
            if current_branch != branch:
                raise ValidationError(
                    f"Existing worktree uses branch '{current_branch}', expected '{branch}': {worktree}"
                )
            base_commit = self._git_at(worktree, "rev-parse", "HEAD")
            return WorktreeContext(worktree, branch, base_commit)

        branch_exists = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=self.repository_root,
            check=False,
        ).returncode == 0
        if branch_exists:
            raise ValidationError(
                f"Branch already exists without its expected worktree: {branch}. "
                "Reuse or remove it explicitly."
            )

        self._git("fetch", "origin", "main")
        base_commit = self._git("rev-parse", "--verify", "origin/main^{commit}")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree), base_commit],
            cwd=self.repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValidationError(f"Could not create task worktree: {result.stderr.strip()}")
        return WorktreeContext(worktree, branch, base_commit)

    def worktree_path(self, task: TaskSpec) -> Path:
        """Place task worktrees beside the primary checkout, outside its diff."""
        slug = re.sub(r"[^a-z0-9-]+", "-", task.task_id.lower()).strip("-")
        return (
            self.repository_root.parent
            / "CodedWorkspace"
            / self.repository_root.name
            / slug
        )

    def task_paths(self, worktree: Path, task: TaskSpec) -> tuple[Path, Path, Path]:
        root = self._inside(worktree, task.workspace.root)
        coding = self._inside(worktree, task.workspace.coding_dir)
        tests = self._inside(worktree, task.workspace.test_dir)
        if not coding.is_relative_to(root) or not tests.is_relative_to(root):
            raise ValidationError("Coding and test paths must be inside the task workspace")
        return root, coding, tests

    def remove_delivered(self, task: TaskSpec, worktree: Path) -> None:
        """Remove a delivered worktree only when no task data can be lost."""
        expected = self.worktree_path(task).resolve()
        candidate = worktree.resolve()
        if candidate != expected:
            raise ValidationError(f"Refusing to remove unexpected worktree path: {candidate}")
        registered = self._git("worktree", "list", "--porcelain")
        if f"worktree {candidate}" not in registered:
            raise ValidationError(f"Worktree is not registered: {candidate}")
        status = self._git_at(candidate, "status", "--porcelain", "--untracked-files=all")
        unexpected = []
        for line in status.splitlines():
            relative = line[3:].strip().strip('"')
            if not any(
                relative == prefix.rstrip("/") or relative.startswith(prefix)
                for prefix in CLEANUP_ONLY_PREFIXES
            ):
                unexpected.append(relative)
        if unexpected:
            raise ValidationError(
                "Refusing to remove delivered worktree with unexpected files: "
                + ", ".join(unexpected)
            )
        self._git("worktree", "remove", "--force", str(candidate))
        self._git("worktree", "prune")

    @staticmethod
    def _inside(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()):
            raise ValidationError(f"Path escapes worktree: {relative}")
        return candidate

    def _git(self, *args: str) -> str:
        return self._git_at(self.repository_root, *args)

    @staticmethod
    def _git_at(repository: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValidationError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()
