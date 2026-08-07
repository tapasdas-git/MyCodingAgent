from __future__ import annotations

from pathlib import Path

import pytest

from mycodeagent.models import TaskIntent, TaskSource, TaskSpec, WorkspaceBoundary


@pytest.fixture
def task() -> TaskSpec:
    return TaskSpec(
        task_id="TASK-1", source=TaskSource.TODO, source_reference="TODO.md",
        state="ready", priority="P1", title="Feature", intent=TaskIntent.FEATURE,
        outcome="Build it", repository=None, dependencies=(),
        architecture_requirements=(), security_requirements=(),
        acceptance_criteria=("Implementation and tests pass",),
        required_files=("workspace/sample/Coding/main.py", "workspace/sample/test/test_main.py"),
        workspace=WorkspaceBoundary("workspace/sample", "workspace/sample/Coding", "workspace/sample/test"),
        raw_section="task",
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=tmp_path, check=True)
    return tmp_path
