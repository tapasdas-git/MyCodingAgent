"""Authoritative deterministic test execution."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .models import TaskSpec, TestResult
from .validator import WorkspaceValidator


class TestRunner:
    def __init__(self, python_executable: str, timeout_seconds: int = 300) -> None:
        self.python_executable = python_executable
        self.timeout_seconds = timeout_seconds

    def run(self, worktree: Path, task: TaskSpec) -> TestResult:
        command = (
            self.python_executable,
            "-m",
            "pytest",
            task.workspace.test_dir,
            "-q",
            "-p",
            "no:cacheprovider",
        )
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=worktree,
                env=environment,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\nTests exceeded {self.timeout_seconds} seconds."
        fingerprint = WorkspaceValidator(worktree, task).fingerprint()
        return TestResult(
            command=command,
            exit_code=exit_code,
            passed=exit_code == 0,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=time.monotonic() - started,
            fingerprint=fingerprint,
        )
