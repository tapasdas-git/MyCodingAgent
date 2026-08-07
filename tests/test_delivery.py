from dataclasses import replace

import pytest

from mycodeagent.delivery import PullRequestDelivery
from mycodeagent.errors import ValidationError
from mycodeagent.models import ExecutionMemory, WorkflowState


def test_delivery_rejects_stale_review_fingerprint(git_repo, task):
    for relative in task.required_files:
        path = git_repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    memory = ExecutionMemory(
        "run", task, state=WorkflowState.DELIVERING,
        worktree=str(git_repo), current_fingerprint="sha256:stale",
    )
    with pytest.raises(ValidationError, match="fingerprint is stale"):
        PullRequestDelivery().deliver(memory)


def test_delivery_rejects_task_repository_that_differs_from_origin(git_repo, task):
    import subprocess

    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/example/MyCodingAgent.git"],
        cwd=git_repo,
        check=True,
    )
    mismatched_task = replace(task, repository="https://github.com/example/MyOmnigent.git")
    memory = ExecutionMemory("run", mismatched_task, state=WorkflowState.DELIVERING)

    with pytest.raises(ValidationError, match="does not match origin remote"):
        PullRequestDelivery._validate_repository(git_repo, memory.task.repository)
