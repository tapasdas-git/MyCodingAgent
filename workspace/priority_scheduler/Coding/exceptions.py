"""Domain exceptions for the priority scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:  # pragma: no cover - mirrors runtime import fallback.
        from .schemas import TaskResult
    except ImportError:  # pragma: no cover - direct path-based imports.
        from schemas import TaskResult


class TaskExecutionError(RuntimeError):
    """Raised when a task fails after exhausting retries or hits a terminal error."""

    def __init__(self, message: str, *, summary: TaskResult | None = None) -> None:
        super().__init__(message)
        self.summary = summary


class TaskTimeoutError(TaskExecutionError):
    """Raised when a task exceeds its configured execution timeout."""
