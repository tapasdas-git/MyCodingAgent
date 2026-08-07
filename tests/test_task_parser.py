from pathlib import Path

import pytest

from mycodeagent.errors import TaskParseError
from mycodeagent.task_parser import select_task


def test_parser_normalizes_complete_workspace_contract(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    todo.write_text("""## TASK-9 | ready | P2 | [FEATURE] Build `workspace/demo/`
- Outcome: Do the work.
- Depends on: None
- Workspace Boundary:
  - Source: `workspace/demo/Coding/`
  - Tests: `workspace/demo/test/`
  - Requirements: `workspace/demo/Coding/requirements.txt`
- Acceptance:
  - Create `main.py`.
  - Create `test_main.py`.
""", encoding="utf-8")
    task = select_task(todo)
    assert task.workspace.root == "workspace/demo"
    assert task.required_files == (
        "workspace/demo/Coding/requirements.txt",
        "workspace/demo/Coding/main.py",
        "workspace/demo/test/test_main.py",
    )


def test_parser_rejects_workspace_escape(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    todo.write_text("""## TASK-9 | ready | P2 | Feature
- Workspace Boundary:
  - Source: `workspace/../bad/Coding/`
  - Tests: `workspace/bad/test/`
- Acceptance:
  - Safe files.
""", encoding="utf-8")
    with pytest.raises(TaskParseError):
        select_task(todo)


def test_parser_rejects_requirements_outside_task_workspace(tmp_path: Path):
    todo = tmp_path / "TODO.md"
    todo.write_text("""## TASK-9 | ready | P2 | Feature
- Workspace Boundary:
  - Source: `workspace/demo/Coding/`
  - Tests: `workspace/demo/test/`
  - Requirements: `workspace/other/Coding/requirements.txt`
- Acceptance:
  - Safe files.
""", encoding="utf-8")

    with pytest.raises(TaskParseError, match="Requirements path must be inside"):
        select_task(todo)
