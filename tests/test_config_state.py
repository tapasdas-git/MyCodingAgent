from dataclasses import replace
from pathlib import Path

import pytest

from mycodeagent.config import load_workflow_config
from mycodeagent.errors import ConfigurationError, IterationLimitError
from mycodeagent.models import ExecutionMemory, WorkflowState
from mycodeagent.state_store import StateStore


def test_role_provider_is_configuration_only(tmp_path: Path):
    path = tmp_path / "runtime.toml"
    path.write_text("""[workflow]
max_cycles = 5
[defaults]
harness = "codex"
model = "codex-model"
effort = "high"
time_limit_seconds = 60
[agents.implementer]
harness = "anthropic"
model = "claude-model"
""", encoding="utf-8")
    config = load_workflow_config(path)
    assert config.role_configs[next(r for r in config.role_configs if r.value == "implementer")].harness == "anthropic"
    assert config.worktree_root == Path("../CodedWorkspace")


def test_worktree_root_is_loaded_from_configuration(tmp_path: Path):
    path = tmp_path / "runtime.toml"
    path.write_text("""[workflow]
max_cycles = 5
[defaults]
harness = "codex"
model = "model"
effort = "high"
time_limit_seconds = 60
[paths]
worktree_root = 'C:\\MyCodingAgent\\worktrees'
""", encoding="utf-8")

    config = load_workflow_config(path)

    assert str(config.worktree_root) == r"C:\MyCodingAgent\worktrees"


def test_max_cycles_is_fixed_at_five(tmp_path: Path):
    path = tmp_path / "runtime.toml"
    path.write_text("harness='codex'\nmodel='m'\neffort='high'\ntime_limit_seconds=1\nmax_cycles=6\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_workflow_config(path)


def test_sixth_cycle_is_refused(git_repo: Path, task):
    memory = ExecutionMemory("run", task, cycle=5, max_cycles=5)
    with pytest.raises(IterationLimitError):
        StateStore(git_repo).start_cycle(memory)


def test_transition_updates_only_selected_todo_heading(git_repo: Path, task):
    todo = git_repo / "TODO.md"
    todo.write_text(
        "## TASK-1 | ready | P1 | Feature\n\n"
        "## TASK-2 | ready | P2 | Other\n",
        encoding="utf-8",
    )
    task = replace(task, source_reference=str(todo))
    memory = ExecutionMemory("run", task)

    StateStore(git_repo).transition(memory, WorkflowState.WORKING)

    assert todo.read_text(encoding="utf-8") == (
        "## TASK-1 | IMPLEMENTING | P1 | Feature\n\n"
        "## TASK-2 | ready | P2 | Other\n"
    )


def test_initialize_marks_received_and_delivery_uses_pr_labels(git_repo: Path, task):
    todo = git_repo / "TODO.md"
    todo.write_text("## TASK-1 | ready | P1 | Feature\n", encoding="utf-8")
    task = replace(task, source_reference=str(todo))
    memory = ExecutionMemory("run", task)
    store = StateStore(git_repo)

    store.initialize(memory)
    assert "| RECEIVED |" in todo.read_text(encoding="utf-8")

    memory.state = WorkflowState.APPROVED
    store.transition(memory, WorkflowState.DELIVERING)
    assert "| CREATING_PR |" in todo.read_text(encoding="utf-8")

    store.transition(memory, WorkflowState.DELIVERED)
    assert "| PR creation complete |" in todo.read_text(encoding="utf-8")
