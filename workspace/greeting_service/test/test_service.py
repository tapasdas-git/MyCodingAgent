"""Tests for the greeting service."""

from __future__ import annotations

import pytest

from workspace.greeting_service.Coding.service import greet


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("World", "Hello, World!"),
        ("  Ada  ", "Hello, Ada!"),
    ],
)
def test_greet_returns_a_formatted_message(name: str, expected: str) -> None:
    """Greet known names with a normalized, deterministic message."""
    assert greet(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        123,
        None,
    ],
)
def test_greet_rejects_invalid_input(name: object) -> None:
    """Reject non-string and blank input with specific exceptions."""
    if isinstance(name, str):
        with pytest.raises(ValueError):
            greet(name)
        return

    with pytest.raises(TypeError):
        greet(name)  # type: ignore[arg-type]
