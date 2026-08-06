from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from schemas import AuditEvent, AuditLogRecord


class BaseAuditObserver:
    observer_name = "base"

    def handle_event(self, event: AuditEvent | dict[str, Any]) -> AuditLogRecord:
        raise NotImplementedError


class MemoryAuditObserver(BaseAuditObserver):
    observer_name = "memory"

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: list[AuditLogRecord] = []
        self._next_sequence_number = 1
        self._metrics = {
            "events_processed": 0,
            "validation_failures": 0,
        }

    def handle_event(self, event: AuditEvent | dict[str, Any]) -> AuditLogRecord:
        validated_event = AuditEvent.model_validate(event)
        try:
            with self._lock:
                sequence_number = self._next_sequence_number
                record = AuditLogRecord.from_event(
                    validated_event,
                    observer_name=self.observer_name,
                    sequence_number=sequence_number,
                )
                self._records.append(record)
                self._next_sequence_number += 1
                self._metrics["events_processed"] += 1
        except Exception:
            with self._lock:
                self._metrics["validation_failures"] += 1
            raise

        return record

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._records)

    def records(self) -> list[AuditLogRecord]:
        with self._lock:
            return list(self._records)

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)


class FileAuditObserver(BaseAuditObserver):
    observer_name = "file"

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._next_sequence_number = 1
        self._metrics = {
            "events_processed": 0,
            "validation_failures": 0,
            "bytes_written": 0,
        }

    def handle_event(self, event: AuditEvent | dict[str, Any]) -> AuditLogRecord:
        validated_event = AuditEvent.model_validate(event)
        try:
            with self._lock:
                sequence_number = self._next_sequence_number
                record = AuditLogRecord.from_event(
                    validated_event,
                    observer_name=self.observer_name,
                    sequence_number=sequence_number,
                )
                payload = record.model_dump(mode="json")
                serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
                encoded = serialized.encode("utf-8")
                with self._path.open("ab") as handle:
                    handle.write(encoded)
                self._next_sequence_number += 1
                self._metrics["events_processed"] += 1
                self._metrics["bytes_written"] += len(encoded)
        except Exception:
            with self._lock:
                self._metrics["validation_failures"] += 1
            raise

        return record

    @property
    def event_count(self) -> int:
        with self._lock:
            return self._metrics["events_processed"]

    def read_records(self) -> list[AuditLogRecord]:
        with self._lock:
            if not self._path.exists():
                return []
            records: list[AuditLogRecord] = []
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        records.append(AuditLogRecord.model_validate_json(line))
            return records

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return dict(self._metrics)
