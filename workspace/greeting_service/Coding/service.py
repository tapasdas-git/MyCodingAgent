"""Greeting service for the greeting workspace task."""

from __future__ import annotations


def greet(name: str) -> str:
    """Return a deterministic greeting for a validated name.

    Args:
        name: The name to greet.

    Returns:
        A greeting string in the form ``"Hello, <name>!"``.

    Raises:
        TypeError: If ``name`` is not a string.
        ValueError: If ``name`` is empty or contains only whitespace.
    """

    if not isinstance(name, str):
        raise TypeError("name must be a string")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be empty")

    return f"Hello, {normalized_name}!"
