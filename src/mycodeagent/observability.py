"""Structured logging, trace correlation, redaction, and artifact storage."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SECRET = re.compile(
    r"(?i)(api[_-]?key|authorization|password|secret|token)\s*[:=]\s*([^\r\n,;]+)"
)
SECRET_KEY = re.compile(r"(?i)(api[_-]?key|authorization|password|secret|token)")


def redact(value: str) -> str:
    return SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


@dataclass(frozen=True)
class TraceContext:
    run_id: str
    task_id: str
    trace_id: str

    @classmethod
    def create(cls, run_id: str, task_id: str) -> "TraceContext":
        return cls(run_id=run_id, task_id=task_id, trace_id=uuid.uuid4().hex)


class EventLogger:
    def __init__(self, root: Path, trace: TraceContext) -> None:
        self.run_dir = root / ".mycodeagent" / "runs" / trace.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.run_dir / "events.jsonl"
        self.task_log_dir = root / "logs"
        self.task_log_dir.mkdir(parents=True, exist_ok=True)
        self.task_path = self.task_log_dir / f"{trace.task_id}.logs"
        self._secure_file(self.path)
        self._secure_file(self.task_path)
        self.trace = trace

    def event(
        self,
        event_type: str,
        *,
        stage: str,
        status: str,
        cycle: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "schema": "mycodeagent.event.v1",
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.trace.run_id,
            "task_id": self.trace.task_id,
            "trace_id": self.trace.trace_id,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "cycle": cycle,
            "details": self._redact_value(details or {}),
        }
        payload = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        self._append(self.path, payload)
        self._append(self.task_path, payload)

    def artifact(self, name: str, content: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        path = self.run_dir / "artifacts" / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(redact(content), encoding="utf-8")
        path.chmod(0o600)
        return path

    @classmethod
    def _redact_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return redact(value)
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if SECRET_KEY.search(str(key)) else cls._redact_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [cls._redact_value(item) for item in value]
        return value

    @staticmethod
    def _secure_file(path: Path) -> None:
        path.touch(exist_ok=True)
        path.chmod(0o600)

    @staticmethod
    def _append(path: Path, payload: str) -> None:
        """Append one complete JSON record using an OS-level append write."""
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            remaining = memoryview(payload.encode("utf-8"))
            while remaining:
                written = os.write(descriptor, remaining)
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
