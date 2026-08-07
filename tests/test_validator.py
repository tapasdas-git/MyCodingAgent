from pathlib import Path

from mycodeagent.validator import WorkspaceValidator


def test_validator_enforces_task_boundary_and_ignores_runtime_cache(git_repo: Path, task):
    for relative in task.required_files:
        path = git_repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    runtime = git_repo / ".mycodeagent/runs/1/memory.json"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("{}", encoding="utf-8")
    codex_runtime = git_repo / ".codex-tmp/session/state.jsonl"
    codex_runtime.parent.mkdir(parents=True)
    codex_runtime.write_text("{}", encoding="utf-8")
    cache = git_repo / "workspace/sample/Coding/__pycache__/main.pyc"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"cache")
    result = WorkspaceValidator(git_repo, task).validate()
    assert result.passed
    assert all(
        ".mycodeagent" not in value
        and ".codex-tmp" not in value
        and "__pycache__" not in value
        for value in result.changed_files
    )


def test_validator_rejects_out_of_scope_change(git_repo: Path, task):
    (git_repo / "outside.py").write_text("bad = True\n", encoding="utf-8")
    result = WorkspaceValidator(git_repo, task).validate()
    assert not result.passed
    assert any("outside allowed" in error for error in result.errors)
