"""Deterministic workspace, artifact, secret, and fingerprint validation."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from .models import TaskSpec, ValidationResult

GENERATED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}
RUNTIME_PREFIXES = (".mycodeagent/", ".codex-tmp/", "logs/")
SECRET_PATTERN = re.compile(
    rb"(?i)(api[_-]?key|secret|password|authorization|token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{8,}"
)


class WorkspaceValidator:
    def __init__(self, worktree: Path, task: TaskSpec) -> None:
        self.worktree = worktree.resolve()
        self.task = task
        self.allowed = tuple((self.worktree / value).resolve() for value in task.workspace.allowed_write_paths())

    def validate(self) -> ValidationResult:
        changed = self.changed_files()
        errors: list[str] = []
        for relative in changed:
            path = (self.worktree / relative).resolve()
            if not path.is_relative_to(self.worktree):
                errors.append(f"Path escapes worktree: {relative}")
                continue
            if not any(path.is_relative_to(allowed) for allowed in self.allowed):
                errors.append(f"Changed file is outside allowed task paths: {relative}")
            if any(part in GENERATED_PARTS for part in path.parts) or path.suffix in GENERATED_SUFFIXES:
                errors.append(f"Generated artifact is not allowed: {relative}")
            if path.is_symlink() and not path.resolve().is_relative_to(self.worktree):
                errors.append(f"Symlink escapes worktree: {relative}")
            if path.is_file() and path.stat().st_size <= 2_000_000:
                try:
                    if SECRET_PATTERN.search(path.read_bytes()):
                        errors.append(f"Potential hardcoded secret in: {relative}")
                except OSError as exc:
                    errors.append(f"Could not inspect {relative}: {exc}")

        for required in self.task.required_files:
            if not (self.worktree / required).is_file():
                errors.append(f"Required file is missing: {required}")
        return ValidationResult(
            passed=not errors,
            errors=tuple(errors),
            changed_files=tuple(changed),
            fingerprint=self.fingerprint(changed),
        )

    def changed_files(self) -> list[str]:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=self.worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        files: list[str] = []
        for line in result.stdout.splitlines():
            value = line[3:]
            if " -> " in value:
                value = value.split(" -> ", 1)[1]
            if value and value not in files:
                files.append(value)
        return sorted(
            value for value in files
            if not value.startswith(RUNTIME_PREFIXES)
            and not any(part in GENERATED_PARTS for part in Path(value).parts)
            and Path(value).suffix not in GENERATED_SUFFIXES
        )

    def fingerprint(self, relative_files: list[str] | tuple[str, ...] | None = None) -> str:
        digest = hashlib.sha256()
        for relative in sorted(relative_files or self.changed_files()):
            path = self.worktree / relative
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            if path.is_file() and not path.is_symlink():
                digest.update(path.read_bytes())
            digest.update(b"\0")
        return f"sha256:{digest.hexdigest()}"
