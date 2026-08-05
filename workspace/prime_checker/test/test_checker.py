from __future__ import annotations

import unittest

from prime_checker.Coding.checker import get_prime_factors, is_prime


class IsPrimeTests(unittest.TestCase):
    def test_recognizes_prime_numbers(self) -> None:
        self.assertTrue(is_prime(7))

    def test_rejects_non_prime_numbers(self) -> None:
        self.assertFalse(is_prime(4))

    def test_rejects_numbers_less_than_or_equal_to_one(self) -> None:
        for value in (1, 0, -3):
            with self.subTest(value=value):
                self.assertFalse(is_prime(value))

    def test_accepts_three_as_prime(self) -> None:
        self.assertTrue(is_prime(3))

    def test_rejects_even_numbers_greater_than_two(self) -> None:
        self.assertFalse(is_prime(26))

    def test_rejects_composite_numbers_that_enter_trial_division_loop(self) -> None:
        self.assertFalse(is_prime(49))

    def test_rejects_composite_numbers_after_incrementing_trial_divisor(self) -> None:
        self.assertFalse(is_prime(121))


class PrimeFactorTests(unittest.TestCase):
    def test_returns_prime_factors_for_composite_number(self) -> None:
        self.assertEqual(get_prime_factors(18), [2, 3, 3])

    def test_returns_single_factor_for_prime_number(self) -> None:
        self.assertEqual(get_prime_factors(13), [13])

    def test_returns_repeated_factors_in_order(self) -> None:
        self.assertEqual(get_prime_factors(60), [2, 2, 3, 5])

    def test_returns_empty_list_for_numbers_less_than_two(self) -> None:
        self.assertEqual(get_prime_factors(1), [])
        self.assertEqual(get_prime_factors(0), [])
