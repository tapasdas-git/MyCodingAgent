"""Tests for the greeting service."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


CODING_DIR = Path(__file__).resolve().parents[1] / "Coding"
if str(CODING_DIR) not in sys.path:
    sys.path.insert(0, str(CODING_DIR))

from service import greet


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("World", "Hello, World!"),
        ("  Ada Lovelace  ", "Hello, Ada Lovelace!"),
    ],
)
def test_greet_returns_expected_message(name: str, expected: str) -> None:
    assert greet(name) == expected


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
    ],
)
def test_greet_rejects_blank_names(name: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        greet(name)


@pytest.mark.parametrize("name", [None, 123, object()])
def test_greet_rejects_non_string_names(name: object) -> None:
    with pytest.raises(TypeError, match="must be a string"):
        greet(name)  # type: ignore[arg-type]
