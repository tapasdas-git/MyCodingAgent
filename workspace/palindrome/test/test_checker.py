from __future__ import annotations

import unittest

from palindrome.Coding.checker import is_palindrome


class IsPalindromeTests(unittest.TestCase):
    def test_ignores_spaces_punctuation_and_casing(self) -> None:
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))

    def test_rejects_non_palindrome(self) -> None:
        self.assertFalse(is_palindrome("Hello World"))

    def test_handles_empty_string(self) -> None:
        self.assertTrue(is_palindrome(""))

    def test_handles_single_character(self) -> None:
        self.assertTrue(is_palindrome("x"))

    def test_keeps_digits_in_comparison(self) -> None:
        self.assertTrue(is_palindrome("12 321"))

    def test_rejects_mismatched_characters_after_normalization(self) -> None:
        self.assertFalse(is_palindrome("abc-123"))
