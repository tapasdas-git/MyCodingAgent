"""Tests for the greeting service."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from service import greet  # noqa: E402


def test_greet_returns_expected_message() -> None:
    """Valid input should produce the deterministic greeting."""

    assert greet("Alice") == "Hello, Alice!"


def test_greet_strips_outer_whitespace() -> None:
    """Names with surrounding whitespace should be normalized."""

    assert greet("  Bob  ") == "Hello, Bob!"


@pytest.mark.parametrize(
    "bad_name, expected_exception",
    [
        (None, TypeError),
        (123, TypeError),
        ("", ValueError),
        ("   ", ValueError),
    ],
)
def test_greet_rejects_invalid_input(
    bad_name: object, expected_exception: type[Exception]
) -> None:
    """Invalid input should fail with a deterministic exception."""

    with pytest.raises(expected_exception):
        greet(bad_name)  # type: ignore[arg-type]
