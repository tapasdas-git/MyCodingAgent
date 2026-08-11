"""Tests for the greeting service."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from service import greet  # noqa: E402


def test_greet_valid_input() -> None:
    """Greeting should include the normalized name."""

    assert greet("Alice") == "Hello, Alice!"
    assert greet("  Bob  ") == "Hello, Bob!"


@pytest.mark.parametrize("value", [None, 42, 3.14, [], {}])
def test_greet_rejects_non_string_input(value: object) -> None:
    """Non-string inputs should raise a type error."""

    with pytest.raises(TypeError):
        greet(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_greet_rejects_blank_input(value: str) -> None:
    """Blank strings should raise a value error."""

    with pytest.raises(ValueError):
        greet(value)

