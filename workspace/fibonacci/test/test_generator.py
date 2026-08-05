from __future__ import annotations

import io
import runpy
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import patch

from fibonacci import fibonacci, main


class FibonacciTests(TestCase):
    def test_fibonacci_zero(self) -> None:
        self.assertEqual(fibonacci(0), [])

    def test_fibonacci_one(self) -> None:
        self.assertEqual(fibonacci(1), [0])

    def test_fibonacci_ten(self) -> None:
        self.assertEqual(
            fibonacci(10),
            [0, 1, 1, 2, 3, 5, 8, 13, 21, 34],
        )

    def test_fibonacci_negative_raises(self) -> None:
        with self.assertRaises(ValueError):
            fibonacci(-1)

    def test_cli_main_prints_sequence(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["5"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(buffer.getvalue(), "0 1 1 2 3\n")

    def test_cli_main_rejects_negative_input(self) -> None:
        buffer = io.StringIO()
        with redirect_stderr(buffer), self.assertRaises(SystemExit) as context:
            main(["-1"])

        self.assertEqual(context.exception.code, 2)
        self.assertIn("n must be non-negative", buffer.getvalue())

    def test_module_entrypoint(self) -> None:
        buffer = io.StringIO()
        with patch("sys.argv", ["fibonacci", "3"]), redirect_stdout(
            buffer
        ), self.assertRaises(SystemExit) as context:
            runpy.run_module("fibonacci.__main__", run_name="__main__")

        self.assertEqual(context.exception.code, 0)
        self.assertEqual(buffer.getvalue(), "0 1 1\n")
