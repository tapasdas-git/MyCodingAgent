from __future__ import annotations

from threading import RLock
from typing import Any, Protocol

from schemas import AuditEvent, AuditLogRecord


class AuditObserver(Protocol):
    observer_name: str

    def handle_event(self, event: AuditEvent | dict[str, Any]) -> AuditLogRecord:
        ...


class EventPublisher:
    def __init__(self) -> None:
        self._lock = RLock()
        self._observers: list[AuditObserver] = []

    def register(self, observer: AuditObserver) -> None:
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)

    def unregister(self, observer: AuditObserver) -> None:
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def observer_count(self) -> int:
        with self._lock:
            return len(self._observers)

    def publish(self, event: AuditEvent | dict[str, Any]) -> list[AuditLogRecord]:
        validated_event = AuditEvent.model_validate(event)
        with self._lock:
            observers = list(self._observers)

        records: list[AuditLogRecord] = []
        for observer in observers:
            records.append(observer.handle_event(validated_event))
        return records

