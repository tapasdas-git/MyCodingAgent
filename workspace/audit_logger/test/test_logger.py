from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError


CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from observers import FileAuditObserver, MemoryAuditObserver
from publisher import EventPublisher
from schemas import AuditEvent, AuditLogRecord


def _event() -> AuditEvent:
    return AuditEvent(
        event_type="USER_LOGIN",
        actor="alice",
        source="auth-service",
        payload={"ip": "127.0.0.1", "success": True},
        occurred_at=datetime(2026, 8, 6, 6, 30, tzinfo=timezone.utc),
    )


def test_publisher_notifies_multiple_observers_and_unregisters(tmp_path: Path) -> None:
    publisher = EventPublisher()
    memory_observer = MemoryAuditObserver()
    file_observer = FileAuditObserver(tmp_path / "audit.log")

    publisher.register(memory_observer)
    publisher.register(file_observer)
    publisher.register(memory_observer)

    first_records = publisher.publish(_event())

    assert publisher.observer_count() == 2
    assert len(first_records) == 2
    assert memory_observer.event_count == 1
    assert file_observer.event_count == 1
    assert memory_observer.metrics()["events_processed"] == 1
    assert file_observer.metrics()["bytes_written"] > 0

    publisher.unregister(memory_observer)
    second_records = publisher.publish(
        _event().model_copy(update={"event_type": "FILE_ACCESS", "actor": "bob"})
    )

    assert len(second_records) == 1
    assert memory_observer.event_count == 1
    assert file_observer.event_count == 2


def test_publish_rejects_invalid_payload() -> None:
    publisher = EventPublisher()
    publisher.register(MemoryAuditObserver())

    with pytest.raises(ValidationError):
        publisher.publish(
            {
                "event_type": "  ",
                "actor": "alice",
                "payload": {},
                "source": "auth-service",
                "occurred_at": datetime(2026, 8, 6, 6, 30, tzinfo=timezone.utc),
            }
        )


def test_audit_log_record_detects_tampering() -> None:
    observer = MemoryAuditObserver()
    record = observer.handle_event(_event())

    assert record.verify_integrity() is True

    tampered = record.model_copy(
        update={
            "event": record.event.model_copy(update={"payload": {"ip": "10.0.0.2", "success": True}})
        }
    )

    assert tampered.verify_integrity() is False


def test_file_observer_persists_valid_json_records(tmp_path: Path) -> None:
    observer = FileAuditObserver(tmp_path / "audit.log")
    record = observer.handle_event(_event())

    written = (tmp_path / "audit.log").read_text(encoding="utf-8").strip().splitlines()
    assert len(written) == 1

    loaded = json.loads(written[0])
    assert loaded["checksum"] == record.checksum

    reconstructed = AuditLogRecord.model_validate_json(written[0])
    assert reconstructed.verify_integrity() is True


def test_observers_allocate_unique_sequence_numbers_under_concurrency(tmp_path: Path) -> None:
    memory_observer = MemoryAuditObserver()
    file_observer = FileAuditObserver(tmp_path / "audit.log")

    def publish_memory() -> int:
        return memory_observer.handle_event(_event()).sequence_number

    def publish_file() -> int:
        return file_observer.handle_event(_event()).sequence_number

    with ThreadPoolExecutor(max_workers=8) as executor:
        memory_sequences = list(executor.map(lambda _: publish_memory(), range(32)))
        file_sequences = list(executor.map(lambda _: publish_file(), range(32)))

    assert sorted(memory_sequences) == list(range(1, 33))
    assert sorted(file_sequences) == list(range(1, 33))
    assert memory_observer.event_count == 32
    assert file_observer.event_count == 32
