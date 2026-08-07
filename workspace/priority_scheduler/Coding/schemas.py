"""Pydantic models for jobs, scheduler configuration, and execution summaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskJob(BaseModel):
    """Validated job definition accepted by the scheduler."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    job_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    priority: int = Field(ge=0, le=100)
    handler: Callable[["TaskJob"], Any | Awaitable[Any]]
    payload: Any = None
    max_retries: int | None = Field(default=None, ge=0, le=100)
    timeout_seconds: float | None = Field(default=None, gt=0)
    retry_backoff_seconds: float | None = Field(default=None, ge=0)

    @field_validator("job_id", "category")
    @classmethod
    def _strip_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped


class SchedulerConfig(BaseModel):
    """Configuration for worker, queue, priority, retry, and timeout limits."""

    model_config = ConfigDict(extra="forbid")

    worker_count: int = Field(gt=0)
    global_concurrency_limit: int = Field(gt=0)
    queue_size_limit: int = Field(gt=0)
    priority_min: int = Field(default=0, ge=0)
    priority_max: int = Field(default=100, ge=0)
    max_retries: int = Field(default=3, ge=0)
    default_timeout_seconds: float = Field(default=5.0, gt=0)
    default_retry_backoff_seconds: float = Field(default=0.05, ge=0)
    retry_backoff_multiplier: float = Field(default=2.0, ge=1.0)
    max_retry_backoff_seconds: float = Field(default=1.0, gt=0)
    timeout_poll_interval_seconds: float = Field(default=0.01, gt=0)
    default_category_concurrency_limit: int = Field(default=1, gt=0)
    category_concurrency_limits: Mapping[str, int] = Field(default_factory=dict)

    @field_validator("priority_max")
    @classmethod
    def _validate_priority_bounds(cls, value: int, info) -> int:
        priority_min = info.data.get("priority_min")
        if priority_min is not None and value < priority_min:
            raise ValueError("priority_max must be greater than or equal to priority_min")
        return value

    @field_validator("category_concurrency_limits")
    @classmethod
    def _validate_category_limits(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        for category, limit in value.items():
            if not category.strip():
                raise ValueError("category names must not be blank")
            if limit <= 0:
                raise ValueError("category concurrency limits must be positive")
        return dict(value)

    @model_validator(mode="after")
    def _validate_limits(self) -> "SchedulerConfig":
        if self.priority_max < self.priority_min:
            raise ValueError("priority_max must be greater than or equal to priority_min")
        return self


class TaskResult(BaseModel):
    """Validated execution summary returned on success or attached to failures."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    category: str
    priority: int
    status: Literal["success", "error", "timeout", "cancelled"]
    attempts: int = Field(ge=0)
    started_at: float = Field(ge=0)
    finished_at: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    result: Any = None
    error_type: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def _validate_timing(self) -> "TaskResult":
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must be greater than or equal to started_at")
        expected_duration = self.finished_at - self.started_at
        if abs(self.duration_seconds - expected_duration) > 1e-9:
            raise ValueError("duration_seconds must match finished_at - started_at")
        return self
