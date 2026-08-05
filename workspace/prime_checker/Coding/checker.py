from __future__ import annotations


def is_prime(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    factor = 5
    while factor * factor <= n:
        if n % factor == 0 or n % (factor + 2) == 0:
            return False
        factor += 6
    return True


def get_prime_factors(n: int) -> list[int]:
    if n < 2:
        return []

    factors: list[int] = []
    remaining = n

    while remaining % 2 == 0:
        factors.append(2)
        remaining //= 2

    divisor = 3
    while divisor * divisor <= remaining:
        while remaining % divisor == 0:
            factors.append(divisor)
            remaining //= divisor
        divisor += 2

    if remaining > 1:
        factors.append(remaining)

    return factors

