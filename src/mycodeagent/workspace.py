"""Git worktree isolation and safe task-workspace resolution."""

from __future__ import annotations

import os
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
    def __init__(self, repository_root: Path, *, worktree_root: Path | None = None) -> None:
        self.repository_root = repository_root.resolve()
        self.worktree_root = (
            worktree_root.resolve()
            if worktree_root is not None
            else (self.repository_root.parent / "CodedWorkspace").resolve()
        )

    def create(self, task: TaskSpec) -> WorktreeContext:
        slug = re.sub(r"[^a-z0-9-]+", "-", task.task_id.lower()).strip("-")
        branch = f"feature/{slug}"
        worktree = self.worktree_path(task)
        if worktree.exists():
            registered = self._git("worktree", "list", "--porcelain", "-z")
            if not self._is_registered_worktree(worktree, registered):
                raise ValidationError(f"Existing path is not a registered worktree: {worktree}")
            current_branch = self._git_at(worktree, "branch", "--show-current")
            if self._branch_key(current_branch) != self._branch_key(branch):
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
        return self.worktree_root / self.repository_root.name / slug

    def task_paths(self, worktree: Path, task: TaskSpec) -> tuple[Path, Path, Path]:
        root = self._inside(worktree, task.workspace.root)
        coding = self._inside(worktree, task.workspace.coding_dir)
        tests = self._inside(worktree, task.workspace.test_dir)
        if not coding.is_relative_to(root) or not tests.is_relative_to(root):
            raise ValidationError("Coding and test paths must be inside the task workspace")
        return root, coding, tests

    def remove_delivered(self, task: TaskSpec, worktree: Path) -> None:
        """Remove a delivered worktree only when no task data can be lost."""
        expected = self.worktree_path(task).resolve(strict=False)
        candidate = worktree.resolve(strict=False)
        if self._path_key(candidate) != self._path_key(expected):
            raise ValidationError(f"Refusing to remove unexpected worktree path: {candidate}")
        registered = self._git("worktree", "list", "--porcelain", "-z")
        if not self._is_registered_worktree(candidate, registered):
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

    @staticmethod
    def _path_key(value: str | Path) -> str:
        """Return a native, case-aware filesystem identity for comparisons."""
        path = Path(value).expanduser().resolve(strict=False)
        return os.path.normcase(os.path.normpath(str(path)))

    @staticmethod
    def _branch_key(value: str) -> str:
        """Normalize Git's full and short local branch representations."""
        branch = value.strip()
        return branch.removeprefix("refs/heads/")

    @staticmethod
    def _registered_worktree_paths(output: str) -> tuple[Path, ...]:
        """Parse worktree paths from newline or NUL-delimited porcelain output."""
        fields = output.replace("\0", "\n").splitlines()
        return tuple(
            Path(field.removeprefix("worktree "))
            for field in fields
            if field.startswith("worktree ")
        )

    def _is_registered_worktree(self, candidate: Path, output: str) -> bool:
        expected = self._path_key(candidate)
        return any(
            self._path_key(registered) == expected
            for registered in self._registered_worktree_paths(output)
        )

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
