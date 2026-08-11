"""Greeting service utilities."""

from __future__ import annotations


def greet(name: str) -> str:
    """Return a deterministic greeting for a validated name.

    Args:
        name: The person or label to greet.

    Returns:
        A formatted greeting string.

    Raises:
        TypeError: If ``name`` is not a string.
        ValueError: If ``name`` is empty or whitespace-only.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    normalized = name.strip()
    if not normalized:
        raise ValueError("name must not be empty")

    return f"Hello, {normalized}!"
