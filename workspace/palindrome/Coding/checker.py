from __future__ import annotations


def is_palindrome(text: str) -> bool:
    normalized = "".join(character.casefold() for character in text if character.isalnum())
    return normalized == normalized[::-1]

