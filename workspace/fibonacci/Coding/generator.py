from __future__ import annotations

import argparse
from typing import List, Optional, Sequence


def fibonacci(n: int) -> List[int]:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return []
    if n == 1:
        return [0]

    sequence = [0, 1]
    while len(sequence) < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Fibonacci sequence")
    parser.add_argument(
        "n",
        type=int,
        help="Number of Fibonacci values to generate",
    )
    args = parser.parse_args(argv)
    if args.n < 0:
        parser.error("n must be non-negative")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    print(" ".join(str(value) for value in fibonacci(args.n)))
    return 0
