from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "system"
    occurred_at: datetime = Field(default_factory=_utc_now)

    @field_validator("event_type", "actor", "source")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("occurred_at")
    @classmethod
    def _validate_occurred_at(cls, value: datetime) -> datetime:
        return _ensure_timezone_aware(value, "occurred_at")


class AuditLogRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: UUID = Field(default_factory=uuid4)
    event: AuditEvent
    observer_name: str
    sequence_number: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=_utc_now)
    checksum: str

    @field_validator("observer_name")
    @classmethod
    def _validate_observer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("timestamp")
    @classmethod
    def _validate_timestamp(cls, value: datetime) -> datetime:
        return _ensure_timezone_aware(value, "timestamp")

    @model_validator(mode="after")
    def _check_checksum(self) -> "AuditLogRecord":
        if self.checksum != self.calculate_checksum():
            raise ValueError("checksum does not match record contents")
        return self

    @classmethod
    def from_event(
        cls,
        event: AuditEvent | dict[str, Any],
        *,
        observer_name: str,
        sequence_number: int,
        timestamp: datetime | None = None,
        record_id: UUID | None = None,
    ) -> "AuditLogRecord":
        validated_event = AuditEvent.model_validate(event)
        resolved_record_id = record_id or uuid4()
        resolved_timestamp = timestamp or _utc_now()
        return cls(
            record_id=resolved_record_id,
            event=validated_event,
            observer_name=observer_name,
            sequence_number=sequence_number,
            timestamp=resolved_timestamp,
            checksum=cls._compute_checksum(
                record_id=resolved_record_id,
                event=validated_event,
                observer_name=observer_name,
                sequence_number=sequence_number,
                timestamp=resolved_timestamp,
            ),
        )

    @classmethod
    def _compute_checksum(
        cls,
        *,
        record_id: UUID,
        event: AuditEvent,
        observer_name: str,
        sequence_number: int,
        timestamp: datetime,
    ) -> str:
        payload = {
            "record_id": str(record_id),
            "event": event.model_dump(mode="json"),
            "observer_name": observer_name,
            "sequence_number": sequence_number,
            "timestamp": timestamp.isoformat(),
        }
        digest = sha256(_canonical_json(payload).encode("utf-8"))
        return digest.hexdigest()

    def calculate_checksum(self) -> str:
        return self._compute_checksum(
            record_id=self.record_id,
            event=self.event,
            observer_name=self.observer_name,
            sequence_number=self.sequence_number,
            timestamp=self.timestamp,
        )

    def verify_integrity(self) -> bool:
        return self.checksum == self.calculate_checksum()
