from __future__ import annotations

import pytest
from pydantic import ValidationError

from workspace.prompt_optimizer.Coding.sanitizer import PromptOptimizer, create_prompt_optimizer
from workspace.prompt_optimizer.Coding.schemas import RawPrompt


def test_redacts_email_api_key_and_credit_card_values() -> None:
    optimizer = PromptOptimizer(prompt_opt_key=None)
    raw_prompt = RawPrompt(
        text=(
            "Email me at jane.doe@example.com, use api_key=sk-live-1234567890abcdefghijkl, "
            "and charge card 4111 1111 1111 1111."
        )
    )

    sanitized = optimizer.sanitize(raw_prompt)

    assert "jane.doe@example.com" not in sanitized.sanitized_text
    assert "sk-live-1234567890abcdefghijkl" not in sanitized.sanitized_text
    assert "4111 1111 1111 1111" not in sanitized.sanitized_text
    assert sanitized.sanitized_text.count("[REDACTED_EMAIL]") == 1
    assert sanitized.sanitized_text.count("[REDACTED_API_KEY]") == 1
    assert sanitized.sanitized_text.count("[REDACTED_CREDIT_CARD]") == 1
    assert [item.kind for item in sanitized.redactions] == [
        "email",
        "api_key",
        "credit_card",
    ]


def test_formatting_returns_structured_system_and_user_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPT_OPT_KEY", "opt-123")
    optimizer = create_prompt_optimizer()
    sanitized = optimizer.sanitize(RawPrompt(text="Hello there"))

    formatted = optimizer.format(sanitized)

    assert formatted.prompt_opt_key == "opt-123"
    assert formatted.system_message.role == "system"
    assert formatted.user_message.role == "user"
    assert "prompt optimization key loaded" in formatted.system_message.content.lower()
    assert formatted.user_message.content == "Hello there"


def test_factory_loads_prompt_opt_key_dynamically(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPT_OPT_KEY", "dynamic-key")

    optimizer = create_prompt_optimizer()

    assert optimizer.prompt_opt_key == "dynamic-key"


def test_raw_prompt_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        RawPrompt(text="   ")


def test_sanitizing_preserves_safe_text_when_no_sensitive_data_is_present() -> None:
    optimizer = PromptOptimizer(prompt_opt_key=None)
    raw_prompt = RawPrompt(text="Draft a concise product summary.")

    sanitized = optimizer.sanitize(raw_prompt)

    assert sanitized.sanitized_text == "Draft a concise product summary."
    assert sanitized.redactions == []


def test_credit_card_redaction_uses_luhn_validation() -> None:
    optimizer = PromptOptimizer(prompt_opt_key=None)
    raw_prompt = RawPrompt(text="Ignore 1234 5678 9012 3456 but redact 4242 4242 4242 4242.")

    sanitized = optimizer.sanitize(raw_prompt)

    assert "1234 5678 9012 3456" in sanitized.sanitized_text
    assert "[REDACTED_CREDIT_CARD]" in sanitized.sanitized_text
