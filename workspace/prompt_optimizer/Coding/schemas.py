from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def _strip_and_validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be blank")
        return cleaned


class RedactionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["email", "api_key", "credit_card"]
    placeholder: str
    value: str


class SanitizedPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_text: str = Field(min_length=1)
    sanitized_text: str = Field(min_length=1)
    redactions: list[RedactionRecord] = Field(default_factory=list)


class SystemMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system"] = "system"
    content: str = Field(min_length=1)


class UserMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user"] = "user"
    content: str = Field(min_length=1)


class FormattedLLMPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_message: SystemMessage
    user_message: UserMessage
    prompt_opt_key: str | None = None
