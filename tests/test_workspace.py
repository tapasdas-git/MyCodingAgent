from pathlib import Path

import subprocess

import pytest

from mycodeagent.errors import ValidationError
from mycodeagent.workspace import WorktreeManager


def test_task_worktree_is_a_sibling_of_primary_checkout(git_repo: Path, task):
    manager = WorktreeManager(git_repo)

    assert manager.worktree_path(task) == (
        git_repo.parent / "CodedWorkspace" / git_repo.name / "task-1"
    )
    assert not manager.worktree_path(task).is_relative_to(git_repo)


def test_task_paths_remain_inside_active_worktree(git_repo: Path, task):
    root, coding, tests = WorktreeManager(git_repo).task_paths(git_repo, task)

    assert root == git_repo / "workspace/sample"
    assert coding == root / "Coding"
    assert tests == root / "test"


def test_delivered_worktree_cleanup_removes_runtime_residue(git_repo: Path, task):
    manager = WorktreeManager(git_repo)
    worktree = manager.worktree_path(task)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/task-1", str(worktree), "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    runtime = worktree / ".codex-tmp" / "trace"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("runtime", encoding="utf-8")

    manager.remove_delivered(task, worktree)

    assert not worktree.exists()


def test_delivered_worktree_cleanup_refuses_unexpected_files(git_repo: Path, task):
    manager = WorktreeManager(git_repo)
    worktree = manager.worktree_path(task)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/task-1", str(worktree), "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    (worktree / "unexpected.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(ValidationError, match="unexpected files"):
        manager.remove_delivered(task, worktree)

    assert worktree.exists()
