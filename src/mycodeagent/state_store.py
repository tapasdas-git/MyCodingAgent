"""Atomic persistent state and execution-memory storage."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .errors import IterationLimitError, ValidationError
from .models import ExecutionMemory, TaskSource, WorkflowState

ALLOWED_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.READY: {WorkflowState.WORKING, WorkflowState.FAILED},
    WorkflowState.WORKING: {WorkflowState.IMPLEMENTING, WorkflowState.NEEDS_INPUT, WorkflowState.FAILED},
    WorkflowState.IMPLEMENTING: {WorkflowState.VALIDATING, WorkflowState.FAILED},
    WorkflowState.VALIDATING: {WorkflowState.TESTING, WorkflowState.CHANGES_REQUESTED, WorkflowState.FAILED},
    WorkflowState.TESTING: {
        WorkflowState.REVIEWING,
        WorkflowState.IMPLEMENTING,
        WorkflowState.CHANGES_REQUESTED,
        WorkflowState.FAILED,
    },
    WorkflowState.REVIEWING: {
        WorkflowState.APPROVED,
        WorkflowState.CHANGES_REQUESTED,
        WorkflowState.NEEDS_INPUT,
        WorkflowState.FAILED,
    },
    WorkflowState.CHANGES_REQUESTED: {WorkflowState.IMPLEMENTING, WorkflowState.NEEDS_INPUT, WorkflowState.FAILED},
    WorkflowState.APPROVED: {WorkflowState.COMPLETED, WorkflowState.DELIVERING, WorkflowState.FAILED},
    WorkflowState.DELIVERING: {WorkflowState.DELIVERED, WorkflowState.APPROVED, WorkflowState.FAILED},
    WorkflowState.NEEDS_INPUT: {WorkflowState.WORKING, WorkflowState.FAILED},
    WorkflowState.FAILED: {WorkflowState.READY},
    WorkflowState.COMPLETED: set(),
    WorkflowState.DELIVERED: set(),
}

TODO_STATUS: dict[WorkflowState, str] = {
    WorkflowState.READY: "RECEIVED",
    WorkflowState.WORKING: "IMPLEMENTING",
    WorkflowState.IMPLEMENTING: "IMPLEMENTING",
    WorkflowState.VALIDATING: "TESTING",
    WorkflowState.TESTING: "TESTING",
    WorkflowState.REVIEWING: "REVIEWING",
    WorkflowState.CHANGES_REQUESTED: "IMPLEMENTING",
    WorkflowState.APPROVED: "APPROVED",
    # Local-only completion has no PR creation and must not claim otherwise.
    WorkflowState.COMPLETED: "APPROVED",
    WorkflowState.DELIVERING: "CREATING_PR",
    WorkflowState.DELIVERED: "PR creation complete",
    WorkflowState.NEEDS_INPUT: "NEEDS_INPUT",
    WorkflowState.FAILED: "FAILED",
}


class StateStore:
    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root / ".mycodeagent"

    def run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    def save_memory(self, memory: ExecutionMemory) -> Path:
        path = self.run_dir(memory.run_id) / "memory.json"
        self._atomic_json(path, memory.to_dict())
        latest = self.root / "tasks" / memory.task.task_id / "latest.json"
        self._atomic_json(
            latest,
            {
                "run_id": memory.run_id,
                "state": memory.state.value,
                "cycle": memory.cycle,
                "memory_path": str(path),
            },
        )
        return path

    def initialize(self, memory: ExecutionMemory) -> Path:
        """Record intake before the first workflow transition."""
        self._sync_todo_status(memory)
        return self.save_memory(memory)

    def load_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def transition(self, memory: ExecutionMemory, target: WorkflowState) -> None:
        allowed = ALLOWED_TRANSITIONS.get(memory.state, set())
        if target not in allowed:
            raise ValidationError(f"Invalid workflow transition: {memory.state.value} -> {target.value}")
        memory.state = target
        self._sync_todo_status(memory)
        self.save_memory(memory)

    def _sync_todo_status(self, memory: ExecutionMemory) -> None:
        """Mirror each workflow transition into the selected TODO heading."""
        if memory.task.source is not TaskSource.TODO:
            return
        todo_path = Path(memory.task.source_reference)
        if not todo_path.is_absolute():
            todo_path = self.root.parent / todo_path
        if not todo_path.exists():
            return
        content = todo_path.read_text(encoding="utf-8")
        heading = re.compile(
            rf"^(##\s+{re.escape(memory.task.task_id)}\s*\|\s*)[^|]+?(\s*\|)",
            re.MULTILINE,
        )
        updated, count = heading.subn(
            rf"\g<1>{TODO_STATUS[memory.state]}\g<2>", content, count=1
        )
        if count != 1:
            raise ValidationError(
                f"Could not update {memory.task.task_id} status in {todo_path}"
            )
        self._atomic_text(todo_path, updated)

    def start_cycle(self, memory: ExecutionMemory) -> int:
        if memory.cycle >= memory.max_cycles:
            raise IterationLimitError(
                f"Task {memory.task.task_id} exhausted {memory.max_cycles} workflow cycles"
            )
        memory.cycle += 1
        self.save_memory(memory)
        return memory.cycle

    @staticmethod
    def _atomic_json(path: Path, value: dict[str, Any]) -> None:
        payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        StateStore._atomic_text(path, payload)

    @staticmethod
    def _atomic_text(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            temp_path = Path(temp_name)
            if temp_path.exists():
                temp_path.unlink()
